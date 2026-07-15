"""
=========================================================
CATÁLOGO DE PROCESOS CRÍTICOS

Este modelo almacena los procesos críticos
gestionados por el sistema.

No contiene lógica.

Representa únicamente el catálogo maestro
de procesos de negocio.
=========================================================
"""

from odoo import models, fields


class IncidentProcess(models.Model):
    """
    Catálogo maestro de procesos.

    Cada registro representa un proceso crítico
    utilizado por el sistema.
    """

    _name = "incident.process"

    _description = "Proceso Crítico"

    _order = "name"

    # -----------------------------------------
    # DATOS GENERALES
    # -----------------------------------------

    code = fields.Char(
        string="Código",
        required=True,
    )

    name = fields.Char(
        string="Proceso",
        required=True,
    )

    active = fields.Boolean(
        string="Activo",
        default=True,
    )