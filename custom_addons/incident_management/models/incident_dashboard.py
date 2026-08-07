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

    @api.depends_context("uid")
    def _compute_metrics(self):
        """
        Calcula los indicadores directamente desde incident.ticket.
        """

        ticket_model = self.env["incident.ticket"]

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

        total_incidents = ticket_model.search_count(
            generated_domain
        )

        pending_incidents = ticket_model.search_count([
            ("state", "=", "created"),
        ])

        assigned_incidents = ticket_model.search_count([
            ("state", "=", "assigned"),
        ])

        in_progress_incidents = ticket_model.search_count([
            ("state", "=", "in_progress"),
        ])

        resolved_incidents = ticket_model.search_count([
            ("state", "=", "resolved"),
        ])

        closed_incidents = ticket_model.search_count([
            ("state", "=", "closed"),
        ])

        reclassified_incidents = ticket_model.search_count([
            ("classification_decision", "=", "accepted"),
        ])

        resolved_tickets = ticket_model.search([
            ("generation_date", "!=", False),
            ("resolved_date", "!=", False),
        ])

        durations = []

        for ticket in resolved_tickets:
            duration = (
                ticket.resolved_date - ticket.generation_date
            ).total_seconds() / 60

            # Evita considerar datos inconsistentes o negativos.
            if duration >= 0:
                durations.append(duration)

        average_resolution = (
            sum(durations) / len(durations)
            if durations
            else 0
        )

        for dashboard in self:
            dashboard.total_incidents = total_incidents
            dashboard.pending_incidents = pending_incidents
            dashboard.assigned_incidents = assigned_incidents
            dashboard.in_progress_incidents = in_progress_incidents
            dashboard.resolved_incidents = resolved_incidents
            dashboard.closed_incidents = closed_incidents
            dashboard.average_resolution_minutes = round(
                average_resolution,
                2,
            )
            dashboard.reclassified_incidents = (
                reclassified_incidents
            )