from odoo import api, fields, models


class IncidentDashboard(models.Model):
    """
    Panel operacional para supervisar la gestión de incidencias.

    No almacena métricas históricas: consulta los datos actuales
    del modelo incident.ticket cada vez que se abre la pantalla.
    """

    _name = "incident.dashboard"
    _description = "Dashboard Operacional de Incidencias"

    name = fields.Char(
        string="Nombre",
        default="Dashboard Operacional",
        readonly=True,
    )

    total_incidents = fields.Integer(
        string="Incidencias generadas",
        compute="_compute_metrics",
    )

    pending_incidents = fields.Integer(
        string="Pendientes de atención",
        compute="_compute_metrics",
    )

    assigned_incidents = fields.Integer(
        string="Asignadas",
        compute="_compute_metrics",
    )

    in_progress_incidents = fields.Integer(
        string="En atención",
        compute="_compute_metrics",
    )

    resolved_incidents = fields.Integer(
        string="Resueltas",
        compute="_compute_metrics",
    )

    closed_incidents = fields.Integer(
        string="Cerradas",
        compute="_compute_metrics",
    )

    average_resolution_minutes = fields.Float(
        string="Tiempo promedio de resolución (min)",
        compute="_compute_metrics",
        digits=(16, 2),
    )

    reclassified_incidents = fields.Integer(
        string="Reclasificaciones aplicadas",
        compute="_compute_metrics",
    )

    backlog_incidents = fields.Integer(
        string="Backlog operativo",
        compute="_compute_metrics",
    )

    recommendation_acceptance_rate = fields.Float(
        string="Recomendaciones aceptadas (%)",
        compute="_compute_metrics",
        digits=(16, 2),
    )

    validated_classification_rate = fields.Float(
        string="Clasificación validada (%)",
        compute="_compute_metrics",
        digits=(16, 2),
    )

    average_assignment_minutes = fields.Float(
        string="Tiempo promedio de asignación (min)",
        compute="_compute_metrics",
        digits=(16, 2),
    )

    # --------------------------------------llevar el SLA al Dashboard
    sla_compliance_rate = fields.Float(
        string="Cumplimiento SLA (%)",
        compute="_compute_metrics",
        digits=(16, 2),
    )

    sla_met_incidents = fields.Integer(
        string="SLA cumplidos",
        compute="_compute_metrics",
    )

    sla_breached_incidents = fields.Integer(
        string="SLA incumplidos",
        compute="_compute_metrics",
    )

    sla_warning_incidents = fields.Integer(
        string="Próximos a vencer",
        compute="_compute_metrics",
    )

    sla_open_breached_incidents = fields.Integer(
        string="Vencidos pendientes",
        compute="_compute_metrics",
    )

    @api.depends_context("uid")
    def _compute_metrics(self):
        """
        Calcula los indicadores directamente desde incident.ticket.
        """

        ticket_model = self.env["incident.ticket"]

        # ---------------------------------------------------------
        # UNIVERSO DE INCIDENCIAS GENERADAS
        # ---------------------------------------------------------

        generated_domain = [
            (
                "state",
                "in",
                [
                    "created",
                    "assigned",
                    "in_progress",
                    "resolved",
                    "closed",
                ],
            )
        ]
        total_incidents = ticket_model.search_count(generated_domain)
        # ---------------------------------------------------------
        # INDICADORES POR ESTADO
        # ---------------------------------------------------------
        pending_incidents = ticket_model.search_count(
            [
                ("state", "=", "created"),
            ]
        )
        assigned_incidents = ticket_model.search_count(
            [
                ("state", "=", "assigned"),
            ]
        )
        in_progress_incidents = ticket_model.search_count(
            [
                ("state", "=", "in_progress"),
            ]
        )
        resolved_incidents = ticket_model.search_count(
            [
                ("state", "=", "resolved"),
            ]
        )
        closed_incidents = ticket_model.search_count(
            [
                ("state", "=", "closed"),
            ]
        )
        # ---------------------------------------------------------
        # BACKLOG OPERATIVO
        # ---------------------------------------------------------
        backlog_incidents = ticket_model.search_count(
            [
                (
                    "state",
                    "in",
                    [
                        "created",
                        "assigned",
                        "in_progress",
                    ],
                )
            ]
        )
        # ---------------------------------------------------------
        # RECLASIFICACIONES
        # ---------------------------------------------------------
        reclassified_incidents = ticket_model.search_count(
            generated_domain
            + [
                (
                    "classification_decision",
                    "=",
                    "accepted",
                )
            ]
        )
        # ---------------------------------------------------------
        # DECISIONES DEL ASESOR
        # ---------------------------------------------------------
        decision_domain = generated_domain + [
            (
                "classification_decision",
                "in",
                [
                    "matched",
                    "accepted",
                    "maintained",
                    "manual",
                ],
            )
        ]
        decided_incidents = ticket_model.search_count(decision_domain)
        accepted_incidents = ticket_model.search_count(
            generated_domain
            + [
                (
                    "classification_decision",
                    "=",
                    "accepted",
                )
            ]
        )
        matched_incidents = ticket_model.search_count(
            generated_domain
            + [
                (
                    "classification_decision",
                    "=",
                    "matched",
                )
            ]
        )
        acceptance_rate = (
            accepted_incidents / decided_incidents * 100 if decided_incidents else 0
        )
        validated_rate = (
            matched_incidents / decided_incidents * 100 if decided_incidents else 0
        )
        # ---------------------------------------------------------
        # TIEMPO PROMEDIO DE RESOLUCIÓN
        # ---------------------------------------------------------
        resolved_tickets = ticket_model.search(
            [
                ("generation_date", "!=", False),
                ("resolved_date", "!=", False),
            ]
        )
        resolution_durations = []
        for ticket in resolved_tickets:
            duration = (
                ticket.resolved_date - ticket.generation_date
            ).total_seconds() / 60
            if duration >= 0:
                resolution_durations.append(duration)
        average_resolution = (
            sum(resolution_durations) / len(resolution_durations)
            if resolution_durations
            else 0
        )
        # ---------------------------------------------------------
        # TIEMPO PROMEDIO DE ASIGNACIÓN
        # ---------------------------------------------------------
        assigned_tickets = ticket_model.search(
            [
                ("generation_date", "!=", False),
                ("assigned_date", "!=", False),
            ]
        )
        assignment_durations = []
        for ticket in assigned_tickets:
            duration = (
                ticket.assigned_date - ticket.generation_date
            ).total_seconds() / 60
            if duration >= 0:
                assignment_durations.append(duration)
        average_assignment = (
            sum(assignment_durations) / len(assignment_durations)
            if assignment_durations
            else 0
        )

        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # INDICADORES SLA
        # ---------------------------------------------------------

        generated_tickets = ticket_model.search(generated_domain)

        sla_met_incidents = 0
        sla_breached_incidents = 0
        sla_warning_incidents = 0
        sla_open_breached_incidents = 0

        for ticket in generated_tickets:

            # Casos ya resueltos: tienen un resultado definitivo de SLA.
            if ticket.resolved_date:

                if ticket.sla_status == "met":
                    sla_met_incidents += 1

                elif ticket.sla_status == "breached":
                    sla_breached_incidents += 1

            # Casos todavía abiertos: son alertas operativas.
            else:

                if ticket.sla_status == "warning":
                    sla_warning_incidents += 1

                elif ticket.sla_status == "breached":
                    sla_open_breached_incidents += 1

        sla_evaluated_incidents = sla_met_incidents + sla_breached_incidents

        sla_compliance_rate = (
            sla_met_incidents / sla_evaluated_incidents * 100
            if sla_evaluated_incidents
            else 0
        )

        # ---------------------------------------------------------
        # ASIGNAR RESULTADOS AL DASHBOARD
        # ---------------------------------------------------------
        for dashboard in self:
            dashboard.total_incidents = total_incidents
            dashboard.pending_incidents = pending_incidents
            dashboard.assigned_incidents = assigned_incidents
            dashboard.in_progress_incidents = in_progress_incidents
            dashboard.resolved_incidents = resolved_incidents
            dashboard.closed_incidents = closed_incidents
            dashboard.backlog_incidents = backlog_incidents
            dashboard.reclassified_incidents = reclassified_incidents
            dashboard.average_resolution_minutes = round(
                average_resolution,
                2,
            )
            dashboard.average_assignment_minutes = round(
                average_assignment,
                2,
            )
            dashboard.recommendation_acceptance_rate = round(
                acceptance_rate,
                2,
            )
            dashboard.validated_classification_rate = round(
                validated_rate,
                2,
            )
            # ------------------------------------------------------
            dashboard.sla_met_incidents = sla_met_incidents
            dashboard.sla_breached_incidents = sla_breached_incidents
            dashboard.sla_warning_incidents = sla_warning_incidents
            dashboard.sla_open_breached_incidents = sla_open_breached_incidents
            dashboard.sla_compliance_rate = round(
                sla_compliance_rate,
                2,
            )
