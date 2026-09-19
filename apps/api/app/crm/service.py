import unicodedata
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.crm.errors import CrmNotFoundError, CrmValidationError
from app.crm.schemas import (
    CrmActivitiesInput,
    CrmActivitiesOutput,
    CrmActivityOutput,
    CrmAddressInput,
    CrmAddressOutput,
    CrmContactCreateInput,
    CrmContactInput,
    CrmContactMethodInput,
    CrmContactMethodOutput,
    CrmContactOutput,
    CrmContactsOutput,
    CrmContactUpdateInput,
    CrmLinkEmailInput,
    CrmLinkEventInput,
    CrmLinkOutput,
    CrmNoteInput,
    CrmNoteOutput,
    CrmOrganizationCreateInput,
    CrmOrganizationInput,
    CrmOrganizationOutput,
    CrmOrganizationsInput,
    CrmOrganizationsOutput,
    CrmSearchContactsInput,
)
from app.db.session import SessionLocal
from app.execution.context import ExecutionContext
from app.models.calendar_reference import CalendarReference
from app.models.crm import (
    CrmActivity,
    CrmAddress,
    CrmContact,
    CrmContactMethod,
    CrmContactTag,
    CrmNote,
    CrmOrganization,
    CrmOrganizationMember,
    CrmOrganizationTag,
    CrmTag,
)
from app.models.email_reference import EmailReference
from app.models.integration_account import IntegrationAccount
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType
from app.services.audit_service import AuditService


class CrmService:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory

    def search_contacts(
        self, context: ExecutionContext, value: CrmSearchContactsInput
    ) -> CrmContactsOutput:
        with self.session_factory() as session:
            query = (
                select(CrmContact)
                .where(CrmContact.user_id == context.user_id)
                .order_by(CrmContact.full_name, CrmContact.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.query:
                query = (
                    query.outerjoin(
                        CrmContactMethod,
                        CrmContactMethod.contact_id == CrmContact.id,
                    )
                    .where(
                        or_(
                            CrmContact.full_name.icontains(value.query, autoescape=True),
                            CrmContact.job_title.icontains(value.query, autoescape=True),
                            CrmContactMethod.normalized_value.icontains(
                                self._normalize_identity(value.query), autoescape=True
                            ),
                        )
                    )
                    .distinct()
                )
            if value.organization_id:
                self._organization(session, context.user_id, value.organization_id)
                query = query.where(CrmContact.organization_id == value.organization_id)
            if value.status:
                query = query.where(CrmContact.status == value.status)
            contacts = list(session.scalars(query))
            return CrmContactsOutput(
                contacts=[self._contact_output(session, item) for item in contacts],
                limit=value.limit,
                offset=value.offset,
            )

    def get_contact(self, context: ExecutionContext, value: CrmContactInput) -> CrmContactOutput:
        with self.session_factory() as session:
            return self._contact_output(
                session, self._contact(session, context.user_id, value.contact_id)
            )

    def list_organizations(
        self, context: ExecutionContext, value: CrmOrganizationsInput
    ) -> CrmOrganizationsOutput:
        with self.session_factory() as session:
            query = (
                select(CrmOrganization)
                .where(CrmOrganization.user_id == context.user_id)
                .order_by(CrmOrganization.name, CrmOrganization.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.query:
                query = query.where(CrmOrganization.name.icontains(value.query, autoescape=True))
            organizations = list(session.scalars(query))
            return CrmOrganizationsOutput(
                organizations=[self._organization_output(session, item) for item in organizations],
                limit=value.limit,
                offset=value.offset,
            )

    def get_organization(
        self, context: ExecutionContext, value: CrmOrganizationInput
    ) -> CrmOrganizationOutput:
        with self.session_factory() as session:
            return self._organization_output(
                session,
                self._organization(session, context.user_id, value.organization_id),
            )

    def list_activities(
        self, context: ExecutionContext, value: CrmActivitiesInput
    ) -> CrmActivitiesOutput:
        with self.session_factory() as session:
            conditions = [CrmActivity.user_id == context.user_id]
            if value.contact_id:
                self._contact(session, context.user_id, value.contact_id)
                conditions.append(CrmActivity.contact_id == value.contact_id)
            if value.organization_id:
                self._organization(session, context.user_id, value.organization_id)
                conditions.append(CrmActivity.organization_id == value.organization_id)
            items = list(
                session.scalars(
                    select(CrmActivity)
                    .where(*conditions)
                    .order_by(CrmActivity.occurred_at.desc(), CrmActivity.id)
                    .offset(value.offset)
                    .limit(value.limit)
                )
            )
            return CrmActivitiesOutput(
                activities=[self._activity_output(item) for item in items],
                limit=value.limit,
                offset=value.offset,
            )

    def create_organization(
        self, context: ExecutionContext, value: CrmOrganizationCreateInput
    ) -> CrmOrganizationOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmOrganization).where(
                    CrmOrganization.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._organization_output(session, existing)
            organization = CrmOrganization(
                user_id=context.user_id,
                name=self._display(value.name),
                normalized_name=self._normalize(value.name),
                website=str(value.website) if value.website else None,
                status=value.status,
                source=value.source,
                created_by_action_id=context.action_id,
            )
            session.add(organization)
            session.flush()
            if value.address:
                session.add(
                    self._address(context.user_id, value.address, organization_id=organization.id)
                )
            self._set_organization_tags(session, context.user_id, organization.id, value.tags)
            self._audit(
                session, context, "crm_organization_created", "crm_organization", organization.id
            )
            session.commit()
            return self._organization_output(session, organization)

    def create_contact(
        self, context: ExecutionContext, value: CrmContactCreateInput
    ) -> CrmContactOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmContact).where(CrmContact.created_by_action_id == context.action_id)
            )
            if existing:
                return self._contact_output(session, existing)
            if value.organization_id:
                self._organization(session, context.user_id, value.organization_id)
            contact = CrmContact(
                user_id=context.user_id,
                organization_id=value.organization_id,
                full_name=self._display(value.full_name),
                normalized_name=self._normalize(value.full_name),
                job_title=self._optional_display(value.job_title),
                website=str(value.website) if value.website else None,
                status=value.status,
                source=value.source,
                created_by_action_id=context.action_id,
            )
            session.add(contact)
            session.flush()
            self._replace_methods(session, context.user_id, contact.id, value.methods)
            if value.address:
                session.add(self._address(context.user_id, value.address, contact_id=contact.id))
            self._set_contact_tags(session, context.user_id, contact.id, value.tags)
            if value.organization_id:
                session.add(
                    CrmOrganizationMember(
                        user_id=context.user_id,
                        organization_id=value.organization_id,
                        contact_id=contact.id,
                        role=contact.job_title,
                    )
                )
            self._audit(session, context, "crm_contact_created", "crm_contact", contact.id)
            session.commit()
            return self._contact_output(session, contact)

    def update_contact(
        self, context: ExecutionContext, value: CrmContactUpdateInput
    ) -> CrmContactOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            contact = self._contact(session, context.user_id, value.contact_id, lock=True)
            if value.full_name is not None:
                contact.full_name = self._display(value.full_name)
                contact.normalized_name = self._normalize(value.full_name)
            if value.clear_job_title or value.job_title is not None:
                contact.job_title = (
                    None if value.clear_job_title else self._optional_display(value.job_title)
                )
            if value.clear_website or value.website is not None:
                contact.website = None if value.clear_website else str(value.website)
            if value.status:
                contact.status = value.status
            if value.clear_organization or value.organization_id is not None:
                new_organization_id = None if value.clear_organization else value.organization_id
                if new_organization_id:
                    self._organization(session, context.user_id, new_organization_id)
                session.execute(
                    delete(CrmOrganizationMember).where(
                        CrmOrganizationMember.user_id == context.user_id,
                        CrmOrganizationMember.contact_id == contact.id,
                    )
                )
                contact.organization_id = new_organization_id
                if new_organization_id:
                    session.add(
                        CrmOrganizationMember(
                            user_id=context.user_id,
                            organization_id=new_organization_id,
                            contact_id=contact.id,
                            role=contact.job_title,
                        )
                    )
            if value.methods is not None:
                self._replace_methods(session, context.user_id, contact.id, value.methods)
            if value.tags is not None:
                self._set_contact_tags(session, context.user_id, contact.id, value.tags)
            self._audit(session, context, "crm_contact_updated", "crm_contact", contact.id)
            session.commit()
            return self._contact_output(session, contact)

    def add_note(self, context: ExecutionContext, value: CrmNoteInput) -> CrmNoteOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmNote).where(CrmNote.created_by_action_id == context.action_id)
            )
            if existing:
                return self._note_output(existing)
            self._target(session, context.user_id, value.contact_id, value.organization_id)
            note = CrmNote(
                user_id=context.user_id,
                contact_id=value.contact_id,
                organization_id=value.organization_id,
                body=value.body,
                source=value.source,
                created_by_action_id=context.action_id,
            )
            session.add(note)
            session.flush()
            self._audit(session, context, "crm_note_added", "crm_note", note.id)
            session.commit()
            return self._note_output(note)

    def link_email(self, context: ExecutionContext, value: CrmLinkEmailInput) -> CrmLinkOutput:
        with self.session_factory() as session:
            self._approved_action(session, context, value.model_dump(mode="json"))
            self._target(session, context.user_id, value.contact_id, value.organization_id)
            reference = session.scalar(
                select(EmailReference)
                .join(IntegrationAccount, IntegrationAccount.id == EmailReference.account_id)
                .where(
                    EmailReference.id == value.email_reference_id,
                    IntegrationAccount.user_id == context.user_id,
                    IntegrationAccount.provider == "gmail",
                )
            )
            if reference is None:
                raise CrmNotFoundError("Email reference was not found")
            return self._link(
                session,
                context,
                contact_id=value.contact_id,
                organization_id=value.organization_id,
                activity_type="email_linked",
                subject="Email reference linked",
                details={
                    "provider": reference.provider,
                    "message_id": reference.message_id,
                    "thread_id": reference.thread_id,
                },
                email_reference_id=reference.id,
            )

    def link_event(self, context: ExecutionContext, value: CrmLinkEventInput) -> CrmLinkOutput:
        with self.session_factory() as session:
            self._approved_action(session, context, value.model_dump(mode="json"))
            self._target(session, context.user_id, value.contact_id, value.organization_id)
            reference = session.scalar(
                select(CalendarReference)
                .join(IntegrationAccount, IntegrationAccount.id == CalendarReference.account_id)
                .where(
                    CalendarReference.id == value.calendar_reference_id,
                    IntegrationAccount.user_id == context.user_id,
                    IntegrationAccount.provider == "google_calendar",
                )
            )
            if reference is None:
                raise CrmNotFoundError("Calendar reference was not found")
            return self._link(
                session,
                context,
                contact_id=value.contact_id,
                organization_id=value.organization_id,
                activity_type="calendar_linked",
                subject="Calendar event reference linked",
                details={
                    "provider": reference.provider,
                    "calendar_id": reference.calendar_id,
                    "event_id": reference.event_id,
                },
                calendar_reference_id=reference.id,
            )

    def _link(
        self,
        session: Session,
        context: ExecutionContext,
        *,
        contact_id: UUID | None,
        organization_id: UUID | None,
        activity_type: str,
        subject: str,
        details: dict[str, object],
        email_reference_id: UUID | None = None,
        calendar_reference_id: UUID | None = None,
    ) -> CrmLinkOutput:
        existing = session.scalar(
            select(CrmActivity).where(CrmActivity.created_by_action_id == context.action_id)
        )
        if existing is None:
            existing = CrmActivity(
                user_id=context.user_id,
                contact_id=contact_id,
                organization_id=organization_id,
                activity_type=activity_type,
                subject=subject,
                details=details,
                source="integration_reference",
                occurred_at=utc_now(),
                email_reference_id=email_reference_id,
                calendar_reference_id=calendar_reference_id,
                created_by_action_id=context.action_id,
            )
            session.add(existing)
            session.flush()
            self._audit(session, context, activity_type, "crm_activity", existing.id)
            session.commit()
        reference_id = email_reference_id or calendar_reference_id
        return CrmLinkOutput(
            activity_id=existing.id,
            contact_id=existing.contact_id,
            organization_id=existing.organization_id,
            reference_id=reference_id,
        )

    @staticmethod
    def _approved_action(
        session: Session, context: ExecutionContext, payload: dict[str, object]
    ) -> TaskAction:
        action = session.scalar(
            select(TaskAction).where(TaskAction.id == context.action_id).with_for_update()
        )
        if action is None or action.input_payload != payload:
            raise CrmValidationError("CRM payload does not match the approved execution action")
        return action

    @staticmethod
    def _contact(
        session: Session, user_id: UUID, contact_id: UUID, *, lock: bool = False
    ) -> CrmContact:
        query = select(CrmContact).where(CrmContact.id == contact_id, CrmContact.user_id == user_id)
        if lock:
            query = query.with_for_update()
        contact = session.scalar(query)
        if contact is None:
            raise CrmNotFoundError("Contact was not found")
        return contact

    @staticmethod
    def _organization(session: Session, user_id: UUID, organization_id: UUID) -> CrmOrganization:
        organization = session.scalar(
            select(CrmOrganization).where(
                CrmOrganization.id == organization_id,
                CrmOrganization.user_id == user_id,
            )
        )
        if organization is None:
            raise CrmNotFoundError("Organization was not found")
        return organization

    def _target(
        self,
        session: Session,
        user_id: UUID,
        contact_id: UUID | None,
        organization_id: UUID | None,
    ) -> None:
        if contact_id:
            self._contact(session, user_id, contact_id)
        if organization_id:
            self._organization(session, user_id, organization_id)

    def _replace_methods(
        self,
        session: Session,
        user_id: UUID,
        contact_id: UUID,
        values: Sequence[CrmContactMethodInput],
    ) -> None:
        session.execute(
            delete(CrmContactMethod).where(
                CrmContactMethod.user_id == user_id,
                CrmContactMethod.contact_id == contact_id,
            )
        )
        for item in values:
            session.add(
                CrmContactMethod(
                    user_id=user_id,
                    contact_id=contact_id,
                    method_type=item.method_type,
                    value=item.value.strip(),
                    normalized_value=self._normalize_method(item.method_type, item.value),
                    label=self._optional_display(item.label),
                    is_primary=item.is_primary,
                )
            )

    def _set_contact_tags(
        self, session: Session, user_id: UUID, contact_id: UUID, values: Sequence[str]
    ) -> None:
        session.execute(
            delete(CrmContactTag).where(
                CrmContactTag.user_id == user_id, CrmContactTag.contact_id == contact_id
            )
        )
        for tag in self._tags(session, user_id, values):
            session.add(CrmContactTag(user_id=user_id, contact_id=contact_id, tag_id=tag.id))

    def _set_organization_tags(
        self, session: Session, user_id: UUID, organization_id: UUID, values: Sequence[str]
    ) -> None:
        session.execute(
            delete(CrmOrganizationTag).where(
                CrmOrganizationTag.user_id == user_id,
                CrmOrganizationTag.organization_id == organization_id,
            )
        )
        for tag in self._tags(session, user_id, values):
            session.add(
                CrmOrganizationTag(user_id=user_id, organization_id=organization_id, tag_id=tag.id)
            )

    def _tags(self, session: Session, user_id: UUID, values: Sequence[str]) -> list[CrmTag]:
        output = []
        seen = set()
        for value in values:
            name = self._display(value)
            normalized = self._normalize(name)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tag = session.scalar(
                select(CrmTag).where(
                    CrmTag.user_id == user_id, CrmTag.normalized_name == normalized
                )
            )
            if tag is None:
                tag = CrmTag(user_id=user_id, name=name, normalized_name=normalized)
                session.add(tag)
                session.flush()
            output.append(tag)
        return output

    @staticmethod
    def _address(
        user_id: UUID,
        value: CrmAddressInput,
        *,
        contact_id: UUID | None = None,
        organization_id: UUID | None = None,
    ) -> CrmAddress:
        return CrmAddress(
            user_id=user_id,
            contact_id=contact_id,
            organization_id=organization_id,
            kind=value.kind,
            line1=value.line1,
            line2=value.line2,
            city=value.city,
            region=value.region,
            postal_code=value.postal_code,
            country_code=value.country_code.upper(),
        )

    def _contact_output(self, session: Session, contact: CrmContact) -> CrmContactOutput:
        methods = list(
            session.scalars(
                select(CrmContactMethod)
                .where(
                    CrmContactMethod.user_id == contact.user_id,
                    CrmContactMethod.contact_id == contact.id,
                )
                .order_by(CrmContactMethod.is_primary.desc(), CrmContactMethod.id)
            )
        )
        addresses = list(
            session.scalars(
                select(CrmAddress).where(
                    CrmAddress.user_id == contact.user_id,
                    CrmAddress.contact_id == contact.id,
                )
            )
        )
        tags = list(
            session.scalars(
                select(CrmTag.name)
                .join(CrmContactTag, CrmContactTag.tag_id == CrmTag.id)
                .where(
                    CrmContactTag.user_id == contact.user_id,
                    CrmContactTag.contact_id == contact.id,
                )
                .order_by(CrmTag.name)
            )
        )
        return CrmContactOutput(
            id=contact.id,
            organization_id=contact.organization_id,
            full_name=contact.full_name,
            job_title=contact.job_title,
            website=contact.website,
            status=contact.status,
            source=contact.source,
            methods=[self._method_output(item) for item in methods],
            addresses=[self._address_output(item) for item in addresses],
            tags=tags,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )

    def _organization_output(
        self, session: Session, organization: CrmOrganization
    ) -> CrmOrganizationOutput:
        addresses = list(
            session.scalars(
                select(CrmAddress).where(
                    CrmAddress.user_id == organization.user_id,
                    CrmAddress.organization_id == organization.id,
                )
            )
        )
        tags = list(
            session.scalars(
                select(CrmTag.name)
                .join(CrmOrganizationTag, CrmOrganizationTag.tag_id == CrmTag.id)
                .where(
                    CrmOrganizationTag.user_id == organization.user_id,
                    CrmOrganizationTag.organization_id == organization.id,
                )
                .order_by(CrmTag.name)
            )
        )
        members = session.scalar(
            select(func.count())
            .select_from(CrmOrganizationMember)
            .where(
                CrmOrganizationMember.user_id == organization.user_id,
                CrmOrganizationMember.organization_id == organization.id,
            )
        )
        return CrmOrganizationOutput(
            id=organization.id,
            name=organization.name,
            website=organization.website,
            status=organization.status,
            source=organization.source,
            addresses=[self._address_output(item) for item in addresses],
            tags=tags,
            member_count=members or 0,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )

    @staticmethod
    def _method_output(value: CrmContactMethod) -> CrmContactMethodOutput:
        return CrmContactMethodOutput(
            id=value.id,
            method_type=value.method_type,
            value=value.value,
            label=value.label,
            is_primary=value.is_primary,
        )

    @staticmethod
    def _address_output(value: CrmAddress) -> CrmAddressOutput:
        return CrmAddressOutput(
            id=value.id,
            kind=value.kind,
            line1=value.line1,
            line2=value.line2,
            city=value.city,
            region=value.region,
            postal_code=value.postal_code,
            country_code=value.country_code,
        )

    @staticmethod
    def _activity_output(value: CrmActivity) -> CrmActivityOutput:
        return CrmActivityOutput(
            id=value.id,
            contact_id=value.contact_id,
            organization_id=value.organization_id,
            activity_type=value.activity_type,
            subject=value.subject,
            details=value.details,
            source=value.source,
            occurred_at=value.occurred_at,
            email_reference_id=value.email_reference_id,
            calendar_reference_id=value.calendar_reference_id,
        )

    @staticmethod
    def _note_output(value: CrmNote) -> CrmNoteOutput:
        return CrmNoteOutput(
            id=value.id,
            contact_id=value.contact_id,
            organization_id=value.organization_id,
            body=value.body,
            source=value.source,
            created_at=value.created_at,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()

    @staticmethod
    def _display(value: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", value).split())

    @classmethod
    def _optional_display(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = cls._display(value)
        return normalized or None

    @classmethod
    def _normalize_identity(cls, value: str) -> str:
        return cls._normalize(value)

    @classmethod
    def _normalize_method(cls, method_type: str, value: str) -> str:
        if method_type == "email":
            return value.strip().casefold()
        prefix = "+" if value.strip().startswith("+") else ""
        return prefix + "".join(character for character in value if character.isdigit())

    @staticmethod
    def _audit(
        session: Session,
        context: ExecutionContext,
        event_type: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        AuditService(session).record(
            actor_type=ActorType.WORKER,
            actor_id=context.user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={},
            correlation_id=context.correlation_id,
        )
