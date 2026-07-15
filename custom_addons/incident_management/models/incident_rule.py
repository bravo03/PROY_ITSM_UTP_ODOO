# Importamos models y fields desde Odoo.
# models permite crear modelos/tablas.
# fields permite definir columnas/campos dentro de la tabla.
from odoo import models, fields


class IncidentRule(models.Model):
    """
    Modelo: Regla de Clasificación.

    Este modelo representa la base de conocimiento del sistema.

    Cada registro equivale a una regla que el motor usará para analizar
    la descripción de una incidencia y sugerir:
    - proceso,
    - aplicación,
    - escenario,
    - grupo resolutor.
    """

    # Nombre técnico del modelo dentro de Odoo.
    _name = "incident.rule"

    # Descripción funcional del modelo.
    _description = "Regla de Clasificación de Incidencias"

    # Nombre visible de la regla.
    # Ejemplo: "Reposición SIM - Activación ICCID".
    name = fields.Char(
        string="Nombre de la regla",
        required=True
    )

    # Campo principal de palabras clave.
    # Aquí se registran varias palabras separadas por coma.
    # Ejemplo: "reposicion, chip, sim, iccid, bloqueo, suspendida"
    keywords = fields.Text(
        string="Palabras clave",
        required=True,
        help="Registrar palabras o frases separadas por coma. Ejemplo: reposicion, chip, sim, iccid"
    )

    # Tipo de coincidencia.
    # Por ahora usaremos 'contiene', pero dejamos el campo preparado
    # para futuras mejoras como coincidencia exacta.
    match_type = fields.Selection([
        ("contains", "Contiene"),
        ("exact", "Coincidencia exacta"),
    ], string="Tipo de coincidencia", default="contains", required=True)

    # Proceso que sugerirá el motor si la regla obtiene el mayor puntaje.
    suggested_process = fields.Char(
        string="Proceso sugerido",
        required=True
    )

    # Aplicación que sugerirá el motor.
    suggested_application = fields.Char(
        string="Aplicación sugerida"
    )

    # Escenario o casuística sugerida.
    suggested_scenario = fields.Char(
        string="Escenario sugerido"
    )

    # Grupo resolutor sugerido.
    suggested_group = fields.Char(
        string="Grupo resolutor sugerido",
        required=True
    )

    # Peso de la regla.
    # Sirve para darle más importancia a reglas más críticas o específicas.
    # Ejemplo: una regla de "ICCID no activo" puede pesar más que una genérica de "chip".
    weight = fields.Integer(
        string="Peso",
        default=1
    )

    # Campo para activar o desactivar la regla sin eliminarla.
    active = fields.Boolean(
        string="Activo",
        default=True
    )