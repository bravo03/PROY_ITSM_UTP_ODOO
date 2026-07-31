# Herramientas principales de Odoo.
from odoo import fields, models


class IncidentTeam(models.Model):
    """
    Catálogo de equipos o grupos resolutores.

    Este modelo representa las bandejas técnicas que recibirán
    las incidencias después de su generación.
    """

    _name = "incident.team"
    _description = "Equipo Resolutor"
    _order = "name"

    # Nombre visible del equipo.
    name = fields.Char(
        string="Equipo resolutor",
        required=True,
    )

    # Código corto para identificar el equipo.
    code = fields.Char(
        string="Código",
        required=True,
    )

    # Permite desactivar equipos sin eliminarlos.
    active = fields.Boolean(
        string="Activo",
        default=True,
    )

    # Descripción funcional del equipo.
    description = fields.Text(
        string="Descripción",
    )

    # Evita registrar códigos duplicados.
    _sql_constraints = [
        (
            "incident_team_code_unique",
            "unique(code)",
            "El código del equipo resolutor debe ser único.",
        ),
    ]