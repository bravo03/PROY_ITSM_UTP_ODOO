from odoo import fields, models


class IncidentApplication(models.Model):
    """
    Catálogo de aplicaciones asociadas a un proceso crítico.

    Ejemplo:
    - Portabilidad -> SISACT
    - Reposición de SIM -> SISACT / EOC
    """

    _name = "incident.application"
    _description = "Aplicación de Incidencia"
    _order = "name"

    name = fields.Char(
        string="Aplicación",
        required=True,
    )

    process_id = fields.Many2one(
        comodel_name="incident.process",
        string="Proceso",
        required=True,
        ondelete="cascade",
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
    )