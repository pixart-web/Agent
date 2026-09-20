import re
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
    KnowledgePermissionError,
)
from app.knowledge.schemas import (
    KnowledgeCreate,
    KnowledgeList,
    KnowledgeRead,
    KnowledgeSearch,
    KnowledgeSearchResult,
    KnowledgeUpdate,
    MemberAdd,
    MemberList,
    MemberRead,
    WorkspaceCreate,
    WorkspaceList,
    WorkspaceRead,
)
from app.models.client_management import CrmClient, CrmProject
from app.models.knowledge import KnowledgeItem, KnowledgeRevision, Workspace, WorkspaceMember
from app.models.user import User

MANAGE_ROLES = frozenset({"owner", "admin"})
EDIT_ROLES = frozenset({"owner", "admin", "member"})


class KnowledgeService:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory

    def create_workspace(self, user_id: UUID, value: WorkspaceCreate) -> WorkspaceRead:
        with self.session_factory() as session, session.begin():
            workspace = Workspace(name=value.name, slug=value.slug, created_by_user_id=user_id)
            session.add(workspace)
            session.flush()
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user_id,
                role="owner",
                created_by_user_id=user_id,
            )
            session.add(member)
            try:
                session.flush()
            except IntegrityError as error:
                raise KnowledgeConflictError("Workspace slug is already in use") from error
            return self._workspace_read(workspace, member.role)

    def list_workspaces(self, user_id: UUID) -> WorkspaceList:
        with self.session_factory() as session:
            rows = session.execute(
                select(Workspace, WorkspaceMember.role)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == user_id)
                .order_by(Workspace.name, Workspace.id)
            ).all()
            return WorkspaceList(
                workspaces=[self._workspace_read(workspace, role) for workspace, role in rows]
            )

    def list_members(self, user_id: UUID, workspace_id: UUID) -> MemberList:
        with self.session_factory() as session:
            membership = self._membership(session, workspace_id, user_id)
            self._require_role(membership, MANAGE_ROLES)
            members = list(
                session.scalars(
                    select(WorkspaceMember)
                    .where(WorkspaceMember.workspace_id == workspace_id)
                    .order_by(WorkspaceMember.created_at, WorkspaceMember.id)
                )
            )
            return MemberList(members=[self._member_read(item) for item in members])

    def add_member(self, user_id: UUID, workspace_id: UUID, value: MemberAdd) -> MemberRead:
        with self.session_factory() as session, session.begin():
            actor = self._membership(session, workspace_id, user_id)
            self._require_role(actor, MANAGE_ROLES)
            if session.get(User, value.user_id) is None:
                raise KnowledgeNotFoundError("Resource not found")
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=value.user_id,
                role=value.role,
                created_by_user_id=user_id,
            )
            session.add(member)
            try:
                session.flush()
            except IntegrityError as error:
                raise KnowledgeConflictError("Workspace member already exists") from error
            return self._member_read(member)

    def create_item(
        self, user_id: UUID, workspace_id: UUID, value: KnowledgeCreate
    ) -> KnowledgeRead:
        with self.session_factory() as session, session.begin():
            membership = self._membership(session, workspace_id, user_id)
            self._require_role(membership, EDIT_ROLES)
            self._validate_scopes(session, user_id, value.client_id, value.project_id)
            item = KnowledgeItem(
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                category=value.category,
                title=value.title,
                content=value.content,
                sensitivity=value.sensitivity,
                client_id=value.client_id,
                project_id=value.project_id,
                source_type=value.source_type,
                source_reference=value.source_reference,
                provenance=value.provenance,
            )
            session.add(item)
            session.flush()
            self._revision(session, item, user_id)
            return self._item_read(item)

    def update_item(
        self, user_id: UUID, workspace_id: UUID, item_id: UUID, value: KnowledgeUpdate
    ) -> KnowledgeRead:
        with self.session_factory() as session, session.begin():
            membership = self._membership(session, workspace_id, user_id)
            self._require_role(membership, EDIT_ROLES)
            item = self._item(session, workspace_id, item_id)
            if membership.role == "member" and item.created_by_user_id != user_id:
                raise KnowledgePermissionError("Insufficient workspace permission")
            if item.status != "draft":
                raise KnowledgeConflictError("Only draft knowledge can be edited")
            for field in value.model_fields_set:
                setattr(item, field, getattr(value, field))
            item.updated_at = utc_now()
            self._revision(session, item, user_id)
            session.flush()
            return self._item_read(item)

    def approve_item(self, user_id: UUID, workspace_id: UUID, item_id: UUID) -> KnowledgeRead:
        with self.session_factory() as session, session.begin():
            membership = self._membership(session, workspace_id, user_id)
            self._require_role(membership, MANAGE_ROLES)
            item = self._item(session, workspace_id, item_id)
            if item.status != "draft":
                raise KnowledgeConflictError("Only draft knowledge can be approved")
            item.status = "approved"
            item.approved_by_user_id = user_id
            item.approved_at = utc_now()
            item.updated_at = utc_now()
            self._revision(session, item, user_id)
            session.flush()
            return self._item_read(item)

    def list_items(
        self,
        user_id: UUID,
        workspace_id: UUID,
        *,
        include_drafts: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> KnowledgeList:
        with self.session_factory() as session:
            membership = self._membership(session, workspace_id, user_id)
            query = select(KnowledgeItem).where(KnowledgeItem.workspace_id == workspace_id)
            if not include_drafts or membership.role == "viewer":
                query = query.where(KnowledgeItem.status == "approved")
            else:
                query = query.where(KnowledgeItem.status != "archived")
            query = self._sensitivity_filter(query, membership.role)
            items = list(
                session.scalars(
                    query.order_by(KnowledgeItem.updated_at.desc(), KnowledgeItem.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            return KnowledgeList(
                items=[self._item_read(item) for item in items], limit=limit, offset=offset
            )

    def search(
        self, user_id: UUID, workspace_id: UUID, value: KnowledgeSearch
    ) -> KnowledgeSearchResult:
        with self.session_factory() as session:
            membership = self._membership(session, workspace_id, user_id)
            query = select(KnowledgeItem).where(
                KnowledgeItem.workspace_id == workspace_id,
                KnowledgeItem.status == "approved",
            )
            query = self._sensitivity_filter(query, membership.role)
            if value.category:
                query = query.where(KnowledgeItem.category == value.category)
            if value.client_id:
                query = query.where(KnowledgeItem.client_id == value.client_id)
            if value.project_id:
                query = query.where(KnowledgeItem.project_id == value.project_id)

            dialect = session.get_bind().dialect.name
            if dialect == "postgresql":
                document = func.to_tsvector(
                    "simple", func.concat(KnowledgeItem.title, " ", KnowledgeItem.content)
                )
                search_tokens = re.findall(r"\w+", value.query.lower(), flags=re.UNICODE)
                terms = func.to_tsquery("simple", " | ".join(search_tokens))
                query = query.where(document.op("@@")(terms)).order_by(
                    func.ts_rank(document, terms).desc(), KnowledgeItem.updated_at.desc()
                )
                method = "postgres_full_text"
            else:
                tokens = [token for token in value.query.lower().split() if len(token) > 2]
                clauses = []
                for token in tokens:
                    pattern = f"%{token}%"
                    clauses.extend(
                        (
                            func.lower(KnowledgeItem.title).like(pattern),
                            func.lower(KnowledgeItem.content).like(pattern),
                        )
                    )
                query = query.where(or_(*clauses)).order_by(KnowledgeItem.updated_at.desc())
                method = "substring_fallback"
            items = list(session.scalars(query.limit(value.limit)))
            return KnowledgeSearchResult(
                items=[self._item_read(item) for item in items], retrieval_method=method
            )

    @staticmethod
    def _membership(session: Session, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
        member = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if member is None:
            raise KnowledgeNotFoundError("Resource not found")
        return member

    @staticmethod
    def _require_role(member: WorkspaceMember, roles: frozenset[str]) -> None:
        if member.role not in roles:
            raise KnowledgePermissionError("Insufficient workspace permission")

    @staticmethod
    def _item(session: Session, workspace_id: UUID, item_id: UUID) -> KnowledgeItem:
        item = session.scalar(
            select(KnowledgeItem).where(
                KnowledgeItem.id == item_id, KnowledgeItem.workspace_id == workspace_id
            )
        )
        if item is None:
            raise KnowledgeNotFoundError("Resource not found")
        return item

    @staticmethod
    def _sensitivity_filter(query, role: str):
        if role == "viewer":
            return query.where(KnowledgeItem.sensitivity == "internal")
        if role == "member":
            return query.where(KnowledgeItem.sensitivity != "restricted")
        return query

    @staticmethod
    def _validate_scopes(
        session: Session, user_id: UUID, client_id: UUID | None, project_id: UUID | None
    ) -> None:
        if (
            client_id
            and session.scalar(
                select(CrmClient.id).where(CrmClient.id == client_id, CrmClient.user_id == user_id)
            )
            is None
        ):
            raise KnowledgeNotFoundError("Resource not found")
        if project_id:
            project = session.scalar(
                select(CrmProject).where(CrmProject.id == project_id, CrmProject.user_id == user_id)
            )
            if project is None or (client_id is not None and project.client_id != client_id):
                raise KnowledgeNotFoundError("Resource not found")

    @staticmethod
    def _revision(session: Session, item: KnowledgeItem, actor_user_id: UUID) -> None:
        session.add(
            KnowledgeRevision(
                knowledge_item_id=item.id,
                workspace_id=item.workspace_id,
                actor_user_id=actor_user_id,
                title=item.title,
                content=item.content,
                status=item.status,
                provenance=item.provenance,
            )
        )

    @staticmethod
    def _workspace_read(item: Workspace, role: str) -> WorkspaceRead:
        return WorkspaceRead(
            id=item.id, name=item.name, slug=item.slug, role=role, created_at=item.created_at
        )

    @staticmethod
    def _member_read(item: WorkspaceMember) -> MemberRead:
        return MemberRead(
            id=item.id, user_id=item.user_id, role=item.role, created_at=item.created_at
        )

    @staticmethod
    def _item_read(item: KnowledgeItem) -> KnowledgeRead:
        return KnowledgeRead(
            id=item.id,
            workspace_id=item.workspace_id,
            category=item.category,
            title=item.title,
            content=item.content,
            status=item.status,
            sensitivity=item.sensitivity,
            client_id=item.client_id,
            project_id=item.project_id,
            source_type=item.source_type,
            source_reference=item.source_reference,
            provenance=item.provenance,
            approved_by_user_id=item.approved_by_user_id,
            approved_at=item.approved_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
