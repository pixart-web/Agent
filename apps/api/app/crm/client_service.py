from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.crm.client_schemas import (
    Client360Output,
    ClientCreateInput,
    ClientInput,
    ClientListInput,
    ClientOutput,
    ClientsOutput,
    ClientUpdateInput,
    HistoryOutput,
    InsightOutput,
    OpportunitiesOutput,
    OpportunityCreateInput,
    OpportunityListInput,
    OpportunityOutput,
    OpportunityUpdateInput,
    PipelineCreateInput,
    PipelineListInput,
    PipelineOutput,
    PipelinesOutput,
    PipelineStageOutput,
    ProjectCreateInput,
    ProjectListInput,
    ProjectOutput,
    ProjectsOutput,
    ProjectUpdateInput,
    TaskLinkInput,
    TaskSummary,
)
from app.crm.errors import CrmConflictError, CrmNotFoundError, CrmValidationError
from app.crm.service import CrmService
from app.db.session import SessionLocal
from app.execution.context import ExecutionContext
from app.models.client_management import (
    CrmClient,
    CrmOpportunity,
    CrmPipeline,
    CrmPipelineStage,
    CrmProject,
    CrmRecordHistory,
    CrmTaskLink,
)
from app.models.command import Command
from app.models.crm import CrmActivity, CrmContact, CrmNote, CrmOrganization
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType
from app.services.audit_service import AuditService


class ClientManagementService:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory
        self.crm = CrmService(session_factory)

    def list_clients(self, context: ExecutionContext, value: ClientListInput) -> ClientsOutput:
        with self.session_factory() as session:
            query = (
                select(CrmClient)
                .join(CrmOrganization, CrmOrganization.id == CrmClient.organization_id)
                .where(CrmClient.user_id == context.user_id)
                .order_by(CrmOrganization.name, CrmClient.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.status:
                query = query.where(CrmClient.lifecycle_status == value.status)
            if value.query:
                query = query.where(CrmOrganization.name.icontains(value.query, autoescape=True))
            clients = list(session.scalars(query))
            return ClientsOutput(
                clients=[self._client_output(session, item) for item in clients],
                limit=value.limit,
                offset=value.offset,
            )

    def get_client_360(self, context: ExecutionContext, value: ClientInput) -> Client360Output:
        with self.session_factory() as session:
            client = self._client(session, context.user_id, value.client_id)
            contacts = list(
                session.scalars(
                    select(CrmContact)
                    .where(
                        CrmContact.user_id == context.user_id,
                        CrmContact.organization_id == client.organization_id,
                    )
                    .order_by(CrmContact.full_name, CrmContact.id)
                )
            )
            contact_ids = [item.id for item in contacts]
            activity_target = CrmActivity.organization_id == client.organization_id
            note_target = CrmNote.organization_id == client.organization_id
            if contact_ids:
                activity_target = or_(activity_target, CrmActivity.contact_id.in_(contact_ids))
                note_target = or_(note_target, CrmNote.contact_id.in_(contact_ids))
            activities = list(
                session.scalars(
                    select(CrmActivity)
                    .where(CrmActivity.user_id == context.user_id, activity_target)
                    .order_by(CrmActivity.occurred_at.desc(), CrmActivity.id.desc())
                    .limit(200)
                )
            )
            projects = list(
                session.scalars(
                    select(CrmProject)
                    .where(
                        CrmProject.user_id == context.user_id,
                        CrmProject.client_id == client.id,
                    )
                    .order_by(CrmProject.updated_at.desc(), CrmProject.id)
                )
            )
            opportunities = list(
                session.scalars(
                    select(CrmOpportunity)
                    .where(
                        CrmOpportunity.user_id == context.user_id,
                        CrmOpportunity.client_id == client.id,
                    )
                    .order_by(CrmOpportunity.updated_at.desc(), CrmOpportunity.id)
                )
            )
            notes = list(
                session.scalars(
                    select(CrmNote)
                    .where(CrmNote.user_id == context.user_id, note_target)
                    .order_by(CrmNote.created_at.desc(), CrmNote.id.desc())
                    .limit(100)
                )
            )
            task_rows = session.execute(
                select(Task, CrmTaskLink.project_id)
                .join(CrmTaskLink, CrmTaskLink.task_id == Task.id)
                .join(Plan, Plan.id == Task.plan_id)
                .join(Command, Command.id == Plan.command_id)
                .where(
                    CrmTaskLink.user_id == context.user_id,
                    CrmTaskLink.client_id == client.id,
                    Command.user_id == context.user_id,
                )
                .order_by(Task.created_at.desc(), Task.id)
            ).all()
            entity_conditions = [
                (CrmRecordHistory.entity_type == "client")
                & (CrmRecordHistory.entity_id == client.id)
            ]
            if projects:
                entity_conditions.append(
                    (CrmRecordHistory.entity_type == "project")
                    & CrmRecordHistory.entity_id.in_([item.id for item in projects])
                )
            if opportunities:
                entity_conditions.append(
                    (CrmRecordHistory.entity_type == "opportunity")
                    & CrmRecordHistory.entity_id.in_([item.id for item in opportunities])
                )
            history = list(
                session.scalars(
                    select(CrmRecordHistory)
                    .where(
                        CrmRecordHistory.user_id == context.user_id,
                        or_(*entity_conditions),
                    )
                    .order_by(
                        CrmRecordHistory.created_at.desc(),
                        CrmRecordHistory.id.desc(),
                    )
                    .limit(100)
                )
            )
            activity_outputs = [self.crm._activity_output(item) for item in activities]
            return Client360Output(
                client=self._client_output(session, client),
                contacts=[self.crm._contact_output(session, item) for item in contacts],
                emails=[item for item in activity_outputs if item.activity_type == "email_linked"],
                meetings=[
                    item for item in activity_outputs if item.activity_type == "calendar_linked"
                ],
                projects=[self._project_output(item) for item in projects],
                tasks=[self._task_output(task, project_id) for task, project_id in task_rows],
                activities=activity_outputs,
                opportunities=[self._opportunity_output(item) for item in opportunities],
                notes=[self.crm._note_output(item) for item in notes],
                history=[self._history_output(item) for item in history],
                insights=self._facts(activities, projects, opportunities),
            )

    def list_projects(self, context: ExecutionContext, value: ProjectListInput) -> ProjectsOutput:
        with self.session_factory() as session:
            self._client(session, context.user_id, value.client_id)
            query = (
                select(CrmProject)
                .where(
                    CrmProject.user_id == context.user_id,
                    CrmProject.client_id == value.client_id,
                )
                .order_by(CrmProject.updated_at.desc(), CrmProject.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.status:
                query = query.where(CrmProject.status == value.status)
            projects = list(session.scalars(query))
            return ProjectsOutput(
                projects=[self._project_output(item) for item in projects],
                limit=value.limit,
                offset=value.offset,
            )

    def list_pipelines(
        self, context: ExecutionContext, value: PipelineListInput
    ) -> PipelinesOutput:
        with self.session_factory() as session:
            pipelines = list(
                session.scalars(
                    select(CrmPipeline)
                    .where(CrmPipeline.user_id == context.user_id)
                    .order_by(
                        CrmPipeline.is_default.desc(),
                        CrmPipeline.name,
                        CrmPipeline.id,
                    )
                    .offset(value.offset)
                    .limit(value.limit)
                )
            )
            return PipelinesOutput(
                pipelines=[self._pipeline_output(session, item) for item in pipelines],
                limit=value.limit,
                offset=value.offset,
            )

    def list_opportunities(
        self, context: ExecutionContext, value: OpportunityListInput
    ) -> OpportunitiesOutput:
        with self.session_factory() as session:
            self._client(session, context.user_id, value.client_id)
            query = (
                select(CrmOpportunity)
                .where(
                    CrmOpportunity.user_id == context.user_id,
                    CrmOpportunity.client_id == value.client_id,
                )
                .order_by(CrmOpportunity.updated_at.desc(), CrmOpportunity.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.status:
                query = query.where(CrmOpportunity.status == value.status)
            opportunities = list(session.scalars(query))
            return OpportunitiesOutput(
                opportunities=[self._opportunity_output(item) for item in opportunities],
                limit=value.limit,
                offset=value.offset,
            )

    def create_client(self, context: ExecutionContext, value: ClientCreateInput) -> ClientOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmClient).where(CrmClient.created_by_action_id == context.action_id)
            )
            if existing:
                return self._client_output(session, existing)
            organization = self.crm._organization(session, context.user_id, value.organization_id)
            duplicate = session.scalar(
                select(CrmClient).where(
                    CrmClient.user_id == context.user_id,
                    CrmClient.organization_id == organization.id,
                )
            )
            if duplicate:
                raise CrmConflictError("Organization is already a client")
            client = CrmClient(
                user_id=context.user_id,
                organization_id=organization.id,
                owner_user_id=context.user_id,
                lifecycle_status=value.lifecycle_status,
                industry=self.crm._optional_display(value.industry),
                summary=value.summary,
                created_by_action_id=context.action_id,
            )
            session.add(client)
            session.flush()
            self._history(session, context, "client", client.id, "created", payload)
            self._audit(session, context, "crm_client_created", "crm_client", client.id)
            session.commit()
            return self._client_output(session, client)

    def update_client(self, context: ExecutionContext, value: ClientUpdateInput) -> ClientOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            client = self._client(session, context.user_id, value.client_id, lock=True)
            if value.lifecycle_status is not None:
                client.lifecycle_status = value.lifecycle_status
            if value.clear_industry or value.industry is not None:
                client.industry = (
                    None if value.clear_industry else self.crm._optional_display(value.industry)
                )
            if value.clear_summary or value.summary is not None:
                client.summary = None if value.clear_summary else value.summary
            self._history(session, context, "client", client.id, "updated", payload)
            self._audit(session, context, "crm_client_updated", "crm_client", client.id)
            session.commit()
            return self._client_output(session, client)

    def create_project(self, context: ExecutionContext, value: ProjectCreateInput) -> ProjectOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmProject).where(CrmProject.created_by_action_id == context.action_id)
            )
            if existing:
                return self._project_output(existing)
            self._client(session, context.user_id, value.client_id)
            project = CrmProject(
                user_id=context.user_id,
                client_id=value.client_id,
                owner_user_id=context.user_id,
                name=self.crm._display(value.name),
                description=value.description,
                status=value.status,
                starts_on=value.starts_on,
                due_on=value.due_on,
                created_by_action_id=context.action_id,
            )
            session.add(project)
            session.flush()
            self._history(session, context, "project", project.id, "created", payload)
            self._audit(
                session,
                context,
                "crm_project_created",
                "crm_project",
                project.id,
            )
            session.commit()
            return self._project_output(project)

    def update_project(self, context: ExecutionContext, value: ProjectUpdateInput) -> ProjectOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            project = self._project(session, context.user_id, value.project_id, lock=True)
            if value.name is not None:
                project.name = self.crm._display(value.name)
            if value.clear_description or value.description is not None:
                project.description = None if value.clear_description else value.description
            if value.status is not None:
                project.status = value.status
            if value.clear_starts_on or value.starts_on is not None:
                project.starts_on = None if value.clear_starts_on else value.starts_on
            if value.clear_due_on or value.due_on is not None:
                project.due_on = None if value.clear_due_on else value.due_on
            if project.starts_on and project.due_on and project.due_on < project.starts_on:
                raise CrmValidationError("Project due date cannot precede its start date")
            self._history(session, context, "project", project.id, "updated", payload)
            self._audit(
                session,
                context,
                "crm_project_updated",
                "crm_project",
                project.id,
            )
            session.commit()
            return self._project_output(project)

    def create_pipeline(
        self, context: ExecutionContext, value: PipelineCreateInput
    ) -> PipelineOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmPipeline).where(CrmPipeline.created_by_action_id == context.action_id)
            )
            if existing:
                return self._pipeline_output(session, existing)
            display_name = self.crm._display(value.name)
            duplicate = session.scalar(
                select(CrmPipeline).where(
                    CrmPipeline.user_id == context.user_id,
                    CrmPipeline.name == display_name,
                )
            )
            if duplicate:
                raise CrmConflictError("Pipeline name is already in use")
            if value.is_default:
                session.execute(
                    update(CrmPipeline)
                    .where(CrmPipeline.user_id == context.user_id)
                    .values(is_default=False)
                )
            pipeline = CrmPipeline(
                user_id=context.user_id,
                name=display_name,
                description=value.description,
                is_default=value.is_default,
                created_by_action_id=context.action_id,
            )
            session.add(pipeline)
            session.flush()
            for stage_value in sorted(value.stages, key=lambda item: item.position):
                session.add(
                    CrmPipelineStage(
                        user_id=context.user_id,
                        pipeline_id=pipeline.id,
                        name=self.crm._display(stage_value.name),
                        position=stage_value.position,
                        default_probability=stage_value.default_probability,
                        is_terminal=stage_value.is_terminal,
                    )
                )
            session.flush()
            self._history(session, context, "pipeline", pipeline.id, "created", payload)
            self._audit(
                session,
                context,
                "crm_pipeline_created",
                "crm_pipeline",
                pipeline.id,
            )
            session.commit()
            return self._pipeline_output(session, pipeline)

    def create_opportunity(
        self, context: ExecutionContext, value: OpportunityCreateInput
    ) -> OpportunityOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmOpportunity).where(
                    CrmOpportunity.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._opportunity_output(existing)
            client = self._client(session, context.user_id, value.client_id)
            stage = self._stage(session, context.user_id, value.pipeline_id, value.stage_id)
            if value.contact_id:
                contact = self.crm._contact(session, context.user_id, value.contact_id)
                if contact.organization_id != client.organization_id:
                    raise CrmValidationError("Contact does not belong to the client")
            opportunity = CrmOpportunity(
                user_id=context.user_id,
                client_id=client.id,
                contact_id=value.contact_id,
                pipeline_id=value.pipeline_id,
                stage_id=stage.id,
                owner_user_id=context.user_id,
                title=self.crm._display(value.title),
                description=value.description,
                amount_minor=value.amount_minor,
                currency=value.currency.upper(),
                probability=(
                    stage.default_probability if value.probability is None else value.probability
                ),
                status=value.status,
                expected_close_on=value.expected_close_on,
                created_by_action_id=context.action_id,
            )
            session.add(opportunity)
            session.flush()
            self._history(
                session,
                context,
                "opportunity",
                opportunity.id,
                "created",
                payload,
            )
            self._audit(
                session,
                context,
                "crm_opportunity_created",
                "crm_opportunity",
                opportunity.id,
            )
            session.commit()
            return self._opportunity_output(opportunity)

    def update_opportunity(
        self, context: ExecutionContext, value: OpportunityUpdateInput
    ) -> OpportunityOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            opportunity = self._opportunity(
                session,
                context.user_id,
                value.opportunity_id,
                lock=True,
            )
            if value.stage_id is not None:
                stage = self._stage(
                    session,
                    context.user_id,
                    opportunity.pipeline_id,
                    value.stage_id,
                )
                opportunity.stage_id = stage.id
            if value.title is not None:
                opportunity.title = self.crm._display(value.title)
            if value.clear_description or value.description is not None:
                opportunity.description = None if value.clear_description else value.description
            if value.amount_minor is not None:
                opportunity.amount_minor = value.amount_minor
            if value.currency is not None:
                opportunity.currency = value.currency.upper()
            if value.probability is not None:
                opportunity.probability = value.probability
            if value.status is not None:
                opportunity.status = value.status
            if value.clear_expected_close_on or value.expected_close_on is not None:
                opportunity.expected_close_on = (
                    None if value.clear_expected_close_on else value.expected_close_on
                )
            self._history(
                session,
                context,
                "opportunity",
                opportunity.id,
                "updated",
                payload,
            )
            self._audit(
                session,
                context,
                "crm_opportunity_updated",
                "crm_opportunity",
                opportunity.id,
            )
            session.commit()
            return self._opportunity_output(opportunity)

    def link_task(self, context: ExecutionContext, value: TaskLinkInput) -> TaskSummary:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(CrmTaskLink).where(CrmTaskLink.created_by_action_id == context.action_id)
            )
            if existing:
                task = session.get(Task, existing.task_id)
                if task is None:
                    raise CrmNotFoundError("Task was not found")
                return self._task_output(task, existing.project_id)
            self._client(session, context.user_id, value.client_id)
            if value.project_id:
                project = self._project(session, context.user_id, value.project_id)
                if project.client_id != value.client_id:
                    raise CrmValidationError("Project does not belong to the client")
            task = session.scalar(
                select(Task)
                .join(Plan, Plan.id == Task.plan_id)
                .join(Command, Command.id == Plan.command_id)
                .where(
                    Task.id == value.task_id,
                    Command.user_id == context.user_id,
                )
            )
            if task is None:
                raise CrmNotFoundError("Task was not found")
            duplicate = session.scalar(
                select(CrmTaskLink).where(
                    CrmTaskLink.user_id == context.user_id,
                    CrmTaskLink.task_id == task.id,
                )
            )
            if duplicate:
                raise CrmConflictError("Task is already linked to a client")
            link = CrmTaskLink(
                user_id=context.user_id,
                client_id=value.client_id,
                project_id=value.project_id,
                task_id=task.id,
                created_by_action_id=context.action_id,
            )
            session.add(link)
            session.flush()
            self._history(
                session,
                context,
                "client",
                value.client_id,
                "task_linked",
                payload,
            )
            self._audit(session, context, "crm_task_linked", "crm_task_link", link.id)
            session.commit()
            return self._task_output(task, link.project_id)

    @staticmethod
    def _approved_action(
        session: Session,
        context: ExecutionContext,
        payload: dict[str, object],
    ) -> None:
        action = session.scalar(
            select(TaskAction).where(TaskAction.id == context.action_id).with_for_update()
        )
        if action is None or action.input_payload != payload:
            raise CrmValidationError("Approved CRM payload does not match execution payload")

    @staticmethod
    def _client(
        session: Session,
        user_id: UUID,
        client_id: UUID,
        *,
        lock: bool = False,
    ) -> CrmClient:
        query = select(CrmClient).where(
            CrmClient.id == client_id,
            CrmClient.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        client = session.scalar(query)
        if client is None:
            raise CrmNotFoundError("Client was not found")
        return client

    @staticmethod
    def _project(
        session: Session,
        user_id: UUID,
        project_id: UUID,
        *,
        lock: bool = False,
    ) -> CrmProject:
        query = select(CrmProject).where(
            CrmProject.id == project_id,
            CrmProject.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        project = session.scalar(query)
        if project is None:
            raise CrmNotFoundError("Project was not found")
        return project

    @staticmethod
    def _opportunity(
        session: Session,
        user_id: UUID,
        opportunity_id: UUID,
        *,
        lock: bool = False,
    ) -> CrmOpportunity:
        query = select(CrmOpportunity).where(
            CrmOpportunity.id == opportunity_id,
            CrmOpportunity.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        opportunity = session.scalar(query)
        if opportunity is None:
            raise CrmNotFoundError("Opportunity was not found")
        return opportunity

    @staticmethod
    def _stage(
        session: Session,
        user_id: UUID,
        pipeline_id: UUID,
        stage_id: UUID,
    ) -> CrmPipelineStage:
        stage = session.scalar(
            select(CrmPipelineStage)
            .join(
                CrmPipeline,
                CrmPipeline.id == CrmPipelineStage.pipeline_id,
            )
            .where(
                CrmPipelineStage.id == stage_id,
                CrmPipelineStage.pipeline_id == pipeline_id,
                CrmPipelineStage.user_id == user_id,
                CrmPipeline.user_id == user_id,
            )
        )
        if stage is None:
            raise CrmNotFoundError("Pipeline stage was not found")
        return stage

    def _client_output(self, session: Session, value: CrmClient) -> ClientOutput:
        organization = self.crm._organization(session, value.user_id, value.organization_id)
        return ClientOutput(
            id=value.id,
            organization=self.crm._organization_output(session, organization),
            owner_user_id=value.owner_user_id,
            lifecycle_status=value.lifecycle_status,
            industry=value.industry,
            summary=value.summary,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _project_output(value: CrmProject) -> ProjectOutput:
        return ProjectOutput(
            id=value.id,
            client_id=value.client_id,
            owner_user_id=value.owner_user_id,
            name=value.name,
            description=value.description,
            status=value.status,
            starts_on=value.starts_on,
            due_on=value.due_on,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _opportunity_output(
        value: CrmOpportunity,
    ) -> OpportunityOutput:
        return OpportunityOutput(
            id=value.id,
            client_id=value.client_id,
            contact_id=value.contact_id,
            pipeline_id=value.pipeline_id,
            stage_id=value.stage_id,
            owner_user_id=value.owner_user_id,
            title=value.title,
            description=value.description,
            amount_minor=value.amount_minor,
            currency=value.currency,
            probability=value.probability,
            status=value.status,
            expected_close_on=value.expected_close_on,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _pipeline_output(session: Session, value: CrmPipeline) -> PipelineOutput:
        stages = list(
            session.scalars(
                select(CrmPipelineStage)
                .where(
                    CrmPipelineStage.user_id == value.user_id,
                    CrmPipelineStage.pipeline_id == value.id,
                )
                .order_by(CrmPipelineStage.position, CrmPipelineStage.id)
            )
        )
        return PipelineOutput(
            id=value.id,
            name=value.name,
            description=value.description,
            is_default=value.is_default,
            stages=[
                PipelineStageOutput(
                    id=item.id,
                    name=item.name,
                    position=item.position,
                    default_probability=item.default_probability,
                    is_terminal=item.is_terminal,
                )
                for item in stages
            ],
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _task_output(task: Task, project_id: UUID | None) -> TaskSummary:
        return TaskSummary(
            id=task.id,
            project_id=project_id,
            title=task.title,
            status=task.status.value,
            agent_id=task.agent_id,
            created_at=task.created_at,
        )

    @staticmethod
    def _history_output(value: CrmRecordHistory) -> HistoryOutput:
        return HistoryOutput(
            id=value.id,
            entity_type=value.entity_type,
            entity_id=value.entity_id,
            event_type=value.event_type,
            changes=value.changes,
            created_at=value.created_at,
        )

    @staticmethod
    def _facts(
        activities: list[CrmActivity],
        projects: list[CrmProject],
        opportunities: list[CrmOpportunity],
    ) -> list[InsightOutput]:
        active_projects = sum(item.status == "active" for item in projects)
        open_opportunities = [item for item in opportunities if item.status == "open"]
        facts = [
            InsightOutput(
                kind="fact",
                provenance="system_fact",
                text=f"{active_projects} active project(s).",
            ),
            InsightOutput(
                kind="fact",
                provenance="system_fact",
                text=(f"{len(open_opportunities)} open opportunity/opportunities."),
            ),
        ]
        if activities:
            facts.append(
                InsightOutput(
                    kind="fact",
                    provenance="system_fact",
                    text=(
                        "Most recent recorded activity: "
                        f"{activities[0].subject} at "
                        f"{activities[0].occurred_at.isoformat()}."
                    ),
                )
            )
        return facts

    @staticmethod
    def _history(
        session: Session,
        context: ExecutionContext,
        entity_type: str,
        entity_id: UUID,
        event_type: str,
        changes: dict[str, object],
    ) -> None:
        session.add(
            CrmRecordHistory(
                user_id=context.user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                changes=changes,
                actor_action_id=context.action_id,
            )
        )

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
