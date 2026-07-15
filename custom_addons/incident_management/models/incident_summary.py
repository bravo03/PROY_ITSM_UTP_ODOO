from odoo import fields, models


class IncidentSummary(models.Model):
    """
    Catálogo de resúmenes válidos según el proceso y la aplicación.
    """

    _name = "incident.summary"
    _description = "Resumen de Incidencia"
    _order = "name"

    name = fields.Char(
        string="Resumen",
        required=True,
    )

    process_id = fields.Many2one(
        comodel_name="incident.process",
        string="Proceso",
        required=True,
        ondelete="cascade",
    )

    application_id = fields.Many2one(
        comodel_name="incident.application",
        string="Aplicación",
        required=True,
        ondelete="cascade",
        domain="[('process_id', '=', process_id)]",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
    )