# Importamos las herramientas del framework Odoo.
# api: permite utilizar decoradores como @api.onchange.
# fields: permite definir los campos del modelo.
# models: permite crear modelos de Odoo.
from odoo import api, fields, models


class IncidentTicket(models.Model):
    """
    Modelo principal para registrar incidencias.

    Almacena:
    - La clasificación seleccionada por el usuario.
    - La descripción libre de la falla.
    - La recomendación generada por el motor inteligente.
    """

    # Nombre técnico utilizado internamente por Odoo.
    _name = "incident.ticket"

    # Nombre descriptivo del modelo.
    _description = "Ticket de Incidencia"

    # Ordena los tickets más recientes primero.
    _order = "id desc"

    # ---------------------------------------------------------
    # DATOS GENERALES DEL TICKET
    # ---------------------------------------------------------

    # Por ahora permanece como "Nuevo".
    # Después se generará automáticamente con una secuencia INC.
    name = fields.Char(
        string="Ticket",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
    )

    # El alcance inicial de la solución es Atención Presencial.
    # Se muestra como valor fijo y no editable.
    channel = fields.Selection(
        [
            ("atp", "Atención Presencial"),
        ],
        string="Canal",
        required=True,
        default="atp",
        readonly=True,
    )

    # Combo con los dos tipos de falla establecidos.
    failure_type = fields.Selection(
        [
            ("postventa", "TRANSACCIÓN POSTVENTA"),
            ("venta", "TRANSACCIÓN VENTA"),
        ],
        string="Tipo de falla",
        required=True,
    )

    # Proceso crítico elegido por el usuario.
    process_id = fields.Many2one(
        comodel_name="incident.process",
        string="Proceso",
        required=True,
        ondelete="restrict",
    )

    # Aplicación asociada al proceso.
    # El filtro dinámico se configurará en la vista XML.
    application_id = fields.Many2one(
        comodel_name="incident.application",
        string="Aplicación",
        required=True,
        ondelete="restrict",
    )

    # Resumen asociado al proceso y aplicación.
    # El filtro dinámico también se configurará en la vista XML.
    summary_id = fields.Many2one(
        comodel_name="incident.summary",
        string="Resumen",
        required=True,
        ondelete="restrict",
    )

    # Campo principal que analizará el motor inteligente.
    description = fields.Text(
        string="Descripción de falla",
        required=True,
    )

    # ---------------------------------------------------------
    # RESULTADO DEL MOTOR INTELIGENTE
    # ---------------------------------------------------------

    suggested_process = fields.Char(
        string="Proceso sugerido",
        readonly=True,
    )

    suggested_application = fields.Char(
        string="Aplicación sugerida",
        readonly=True,
    )

    suggested_scenario = fields.Char(
        string="Escenario sugerido",
        readonly=True,
    )

    suggested_group = fields.Char(
        string="Grupo resolutor sugerido",
        readonly=True,
    )

    confidence = fields.Float(
        string="Nivel de coincidencia (%)",
        readonly=True,
    )

    # Nombre de la regla que obtuvo el mayor puntaje.
    applied_rule = fields.Char(
        string="Regla aplicada",
        readonly=True
    )

    # Palabras o frases encontradas en la descripción.
    matched_patterns = fields.Text(
        string="Patrones encontrados",
        readonly=True
    )

    is_reclassified = fields.Boolean(
        string="Reclasificación sugerida",
        readonly=True,
    )

    reclassification_reason = fields.Text(
        string="Motivo de reclasificación",
        readonly=True,
    )

    # Estado funcional del ticket.
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("analyzed", "Analizado"),
            ("assigned", "Asignado"),
            ("closed", "Cerrado"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
    )

    # ---------------------------------------------------------
    # COMBOS DEPENDIENTES
    # ---------------------------------------------------------

    @api.onchange("process_id")
    def _onchange_process_id(self):
        """
        Limpia la aplicación y el resumen cuando cambia el proceso.

        Evita conservar una aplicación o un resumen que pertenezcan
        al proceso seleccionado anteriormente.
        """

        self.application_id = False
        self.summary_id = False

    @api.onchange("application_id")
    def _onchange_application_id(self):
        """
        Limpia el resumen cuando cambia la aplicación.

        Evita conservar un resumen que no corresponda a la nueva
        aplicación seleccionada.
        """

        self.summary_id = False

    # ---------------------------------------------------------
    # ANÁLISIS DE LA INCIDENCIA
    # ---------------------------------------------------------

    def action_analyze_incident(self):
        """
        Envía la descripción al motor inteligente y compara:

        - Proceso seleccionado por el usuario.
        - Proceso sugerido por el motor.

        Cuando son diferentes, registra una recomendación
        de reclasificación.
        """

        for ticket in self:

            # Obtiene el componente encargado de analizar el texto.
            engine = self.env["classification.engine"]

            # Envía la descripción y recibe la recomendación.
            result = engine.analyze(ticket.description)

            # Completa los campos de resultado.
            ticket.suggested_process = result.get("process", "")
            ticket.suggested_application = result.get("application", "")
            ticket.suggested_scenario = result.get("scenario", "")
            ticket.suggested_group = result.get("group", "")
            ticket.confidence = result.get("confidence", 0)


            # Guarda el nombre de la regla utilizada por el motor.
            ticket.applied_rule = result.get("rule_name", "")

            # Recupera la lista de palabras o patrones encontrados.
            matches = result.get("matches", [])

            # Convierte la lista en un texto legible para el usuario.
            if matches:
                ticket.matched_patterns = " • ".join(matches)
            else:
                ticket.matched_patterns = (
                    "No se encontraron patrones coincidentes."
                )

            # Obtiene el nombre visible del proceso seleccionado.
            selected_process = (
                ticket.process_id.name or ""
            ).strip().lower()

            # Obtiene el proceso sugerido por el motor.
            suggested_process = (
                ticket.suggested_process or ""
            ).strip().lower()

            # Solo se considera reclasificación cuando el motor
            # efectivamente encontró un proceso diferente.
            if (
                selected_process
                and suggested_process
                and selected_process != suggested_process
            ):
                ticket.is_reclassified = True
                ticket.reclassification_reason = (
                    f"El usuario seleccionó «{ticket.process_id.name}», "
                    f"pero el análisis de la descripción recomienda "
                    f"«{ticket.suggested_process}» con una confianza de "
                    f"{ticket.confidence} %."
                )
            else:
                ticket.is_reclassified = False

                if suggested_process:
                    ticket.reclassification_reason = (
                        "La clasificación seleccionada coincide con "
                        "el análisis de la descripción."
                    )
                else:
                    ticket.reclassification_reason = (
                        "No se encontraron coincidencias suficientes. "
                        "Se requiere revisión manual."
                    )

            # Marca el ticket como analizado.
            ticket.state = "analyzed"