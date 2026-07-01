from odoo import models, fields


class IncidentTicket(models.Model):
    _name = "incident.ticket"
    _description = "Ticket de Incidencia"

    name = fields.Char(string="Ticket", required=True, copy=False, default="Nuevo")
    channel = fields.Selection([
        ("atp", "Atención Presencial"),
        ("sac", "Servicio al Cliente Móvil"),
        ("fijo", "Atención Fija"),
        ("dmm", "Mercado Masivo"),
        ("otros", "Otros"),
    ], string="Canal", required=True)

    failure_type = fields.Char(string="Tipo de falla")
    process = fields.Char(string="Proceso seleccionado por usuario")
    application = fields.Char(string="Aplicación")
    summary = fields.Char(string="Resumen")
    description = fields.Text(string="Descripción de falla", required=True)

    suggested_process = fields.Char(string="Proceso sugerido")
    suggested_application = fields.Char(string="Aplicación sugerida")
    suggested_scenario = fields.Char(string="Escenario sugerido")
    suggested_group = fields.Char(string="Grupo resolutor sugerido")
    confidence = fields.Float(string="Nivel de confianza (%)")

    state = fields.Selection([
        ("draft", "Borrador"),
        ("analyzed", "Analizado"),
        ("assigned", "Asignado"),
        ("closed", "Cerrado"),
    ], string="Estado", default="draft")