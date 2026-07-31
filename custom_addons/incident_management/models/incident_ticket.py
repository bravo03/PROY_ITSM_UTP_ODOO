# Herramientas principales del framework Odoo.
from odoo import api, fields, models
from odoo.exceptions import UserError


class IncidentTicket(models.Model):
    """
    Modelo principal para registrar incidencias desde el Portal CAC.

    Flujo:

    1. El Asesor CAC registra la clasificación inicial.
    2. El ITSM Copilot analiza la descripción.
    3. El sistema compara la selección con la recomendación.
    4. El asesor puede aceptar o mantener su clasificación.
    5. Finalmente se genera el número INC.
    """

    _name = "incident.ticket"
    _description = "Ticket de Incidencia"
    _order = "id desc"

    # ---------------------------------------------------------
    # DATOS GENERALES
    # ---------------------------------------------------------

    # El código se genera únicamente cuando se confirma la incidencia.
    name = fields.Char(
        string="Número de incidencia",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
    )

    # El alcance inicial está enfocado en los Centros de Atención.
    channel = fields.Selection(
        [
            ("atp", "Atención Presencial"),
        ],
        string="Canal",
        required=True,
        default="atp",
        readonly=True,
    )

    failure_type = fields.Selection(
        [
            ("postventa", "TRANSACCIÓN POSTVENTA"),
            ("venta", "TRANSACCIÓN VENTA"),
        ],
        string="Tipo de falla",
        required=True,
    )

    process_id = fields.Many2one(
        comodel_name="incident.process",
        string="Proceso",
        required=True,
        ondelete="restrict",
    )

    application_id = fields.Many2one(
        comodel_name="incident.application",
        string="Aplicación",
        required=True,
        ondelete="restrict",
    )

    summary_id = fields.Many2one(
        comodel_name="incident.summary",
        string="Resumen",
        required=True,
        ondelete="restrict",
    )

    description = fields.Text(
        string="Descripción de falla",
        required=True,
    )

    # Evidencias adjuntas por el Asesor CAC.
    evidence_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="incident_ticket_attachment_rel",
        column1="ticket_id",
        column2="attachment_id",
        string="Evidencias",
    )

    # ---------------------------------------------------------
    # RESULTADO DEL ITSM COPILOT
    # ---------------------------------------------------------

    suggested_process = fields.Char(
        string="Proceso recomendado",
        readonly=True,
    )

    suggested_application = fields.Char(
        string="Aplicación recomendada",
        readonly=True,
    )

    suggested_scenario = fields.Char(
        string="Escenario recomendado",
        readonly=True,
    )

    suggested_group = fields.Char(
        string="Grupo resolutor recomendado",
        readonly=True,
    )



    # ---------------------------------------------------------
    # ASIGNACIÓN OPERATIVA
    # ---------------------------------------------------------

    # Equipo resolutor al que será enviada la incidencia.
    assigned_team_id = fields.Many2one(
        comodel_name="incident.team",
        string="Equipo resolutor asignado",
        readonly=True,
        ondelete="restrict",
    )

    # Fecha y hora en la que la incidencia fue asignada.
    assigned_date = fields.Datetime(
        string="Fecha de asignación",
        readonly=True,
    )

     # ---------------------------------------------------------

    confidence = fields.Float(
        string="Nivel de coincidencia (%)",
        readonly=True,
    )

    applied_rule = fields.Char(
        string="Regla aplicada",
        readonly=True,
    )

    matched_patterns = fields.Text(
        string="Patrones encontrados",
        readonly=True,
    )

    is_reclassified = fields.Boolean(
        string="Reclasificación sugerida",
        readonly=True,
    )

    reclassification_reason = fields.Text(
        string="Explicación de la recomendación",
        readonly=True,
    )

    # ---------------------------------------------------------
    # TRAZABILIDAD DE LA DECISIÓN
    # ---------------------------------------------------------

    classification_decision = fields.Selection(
        [
            ("pending", "Pendiente de decisión"),
            ("matched", "Clasificación validada"),
            ("accepted", "Recomendación aceptada"),
            ("maintained", "Clasificación original mantenida"),
            ("manual", "Generado para revisión manual"),
        ],
        string="Decisión del asesor",
        default="pending",
        readonly=True,
    )

    analysis_date = fields.Datetime(
        string="Fecha de análisis",
        readonly=True,
    )

    generation_date = fields.Datetime(
        string="Fecha de generación",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("analyzed", "Analizado"),
            ("created", "Incidencia generada"),
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
        Limpia aplicación y resumen cuando cambia el proceso.
        """

        self.application_id = False
        self.summary_id = False

    @api.onchange("application_id")
    def _onchange_application_id(self):
        """
        Limpia el resumen cuando cambia la aplicación.
        """

        self.summary_id = False

    # ---------------------------------------------------------
    # ANÁLISIS DE LA INCIDENCIA
    # ---------------------------------------------------------

    
    def action_register_incident(self):
        """
        Acción principal ejecutada por el Asesor CAC.
        Valida los requisitos mínimos y ejecuta automáticamente
        el ITSM Copilot antes de permitir la generación.
        """
        self.ensure_one()
    # -----------------------------------------------------
    # 1. VALIDAR EVIDENCIA
    # -----------------------------------------------------
        if not self.evidence_ids:
            raise UserError(
                "Estimado usuario, debe adjuntar al menos una evidencia "
                "antes de registrar la incidencia."
            )
    # -----------------------------------------------------
    # 2. EJECUTAR AUTOMÁTICAMENTE EL ITSM COPILOT
    # -----------------------------------------------------
        self.action_analyze_incident()
    # -----------------------------------------------------
    # 3. NO GENERAR TODAVÍA LA INCIDENCIA
    # -----------------------------------------------------
    # El análisis cambia el estado a 'analyzed'.
    # La vista mostrará ahora el resultado del ITSM Copilot.
    # El Asesor CAC deberá revisar la recomendación antes
    # de confirmar definitivamente la generación.

        return True
    
    def action_analyze_incident(self):
        """
        Envía la descripción al motor y presenta la recomendación.
        Este método todavía no genera el número INC.
        """
        for ticket in self:
            engine = self.env["classification.engine"]

            # Ejecuta el motor de clasificación.
            result = engine.analyze(ticket.description)

            # Guarda los resultados del análisis.
            ticket.suggested_process = result.get("process", "")
            ticket.suggested_application = result.get("application", "")
            ticket.suggested_scenario = result.get("scenario", "")
            ticket.suggested_group = result.get("group", "")
            ticket.confidence = result.get("confidence", 0)
            ticket.applied_rule = result.get("rule_name", "")

            # Convierte la lista de coincidencias en texto legible.
            matches = result.get("matches", [])

            if matches:
                ticket.matched_patterns = " • ".join(matches)
            else:
                ticket.matched_patterns = (
                    "No se encontraron patrones coincidentes."
                )

            # Obtiene los procesos para compararlos.
            selected_process = self._normalize_text(
                ticket.process_id.name
            )

            suggested_process = self._normalize_text(
                ticket.suggested_process
            )

            # Registra la fecha de ejecución del motor.
            ticket.analysis_date = fields.Datetime.now()
            ticket.classification_decision = "pending"

            # Existe una recomendación diferente.
            if (
                selected_process
                and suggested_process
                and selected_process != suggested_process
            ):
                ticket.is_reclassified = True

                ticket.reclassification_reason = (
                    f"El Asesor CAC seleccionó "
                    f"«{ticket.process_id.name}», pero el análisis de "
                    f"la descripción recomienda "
                    f"«{ticket.suggested_process}», con un nivel de "
                    f"coincidencia de {ticket.confidence} %."
                )

            # La selección coincide con la recomendación.
            elif suggested_process:
                ticket.is_reclassified = False
                ticket.classification_decision = "matched"

                ticket.reclassification_reason = (
                    "La clasificación seleccionada coincide con el "
                    "resultado obtenido por el ITSM Copilot."
                )

            # El motor no encontró coincidencias.
            else:
                ticket.is_reclassified = False
                ticket.classification_decision = "manual"

                ticket.reclassification_reason = (
                    "No se encontraron coincidencias suficientes. "
                    "La incidencia puede generarse para revisión manual "
                    "del soporte N1."
                )

            ticket.state = "analyzed"

    # ---------------------------------------------------------
    # DECISIÓN DEL ASESOR CAC
    # ---------------------------------------------------------

    def action_apply_recommendation(self):
        """
        Aplica la clasificación recomendada por el ITSM Copilot.
        Actualiza el formulario para que el Asesor CAC pueda revisar
        la clasificación corregida antes de confirmar la generación.
        Este método NO genera todavía el número INC.        
        """

        self.ensure_one()

        if not self.suggested_process:
            raise UserError(
                "No existe una recomendación que pueda aplicarse."
            )

        # Busca el proceso recomendado en el catálogo.
        recommended_process = self._find_record_by_normalized_name(
            model_name="incident.process",
            expected_name=self.suggested_process,
        )

        if not recommended_process:
            raise UserError(
                "El proceso recomendado no está registrado en el "
                "catálogo de procesos críticos."
            )

        original_process = self.process_id.name
        self.process_id = recommended_process

        # Busca la aplicación asociada al proceso recomendado.
        recommended_application = self._find_record_by_normalized_name(
            model_name="incident.application",
            expected_name=self.suggested_application,
            extra_domain=[
                ("process_id", "=", recommended_process.id),
            ],
        )

        if recommended_application:
            self.application_id = recommended_application

        # Intenta identificar un resumen o escenario equivalente.
        summary_domain = [
            ("process_id", "=", recommended_process.id),
        ]

        if recommended_application:
            summary_domain.append(
                ("application_id", "=", recommended_application.id)
            )

        recommended_summary = self._find_record_by_normalized_name(
            model_name="incident.summary",
            expected_name=self.suggested_scenario,
            extra_domain=summary_domain,
        )

        if recommended_summary:
            self.summary_id = recommended_summary

        self.classification_decision = "accepted"
        self.is_reclassified = True

        self.reclassification_reason = (
        f"El Asesor CAC aceptó la recomendación del ITSM Copilot. "
        f"La incidencia fue reclasificada de "
        f"«{original_process}» a «{recommended_process.name}»."
        f"Revise la clasificación actualizada antes de confirmar "
        f"la generación de la incidencia."
        )

        return True
###################################################################################
    def action_confirm_generation(self):
        """
        Confirma la creación definitiva de la incidencia.

        Esta acción se ejecuta después de que el Asesor CAC
        revisó el resultado del ITSM Copilot y tomó una decisión.

        Antes de generar el INC, valida el estado del análisis,
        la decisión del asesor y la evidencia adjunta.
        """

        self.ensure_one()

        # -----------------------------------------------------
        # 1. VALIDAR QUE EL TICKET FUE ANALIZADO
        # -----------------------------------------------------

        if self.state != "analyzed":
            raise UserError(
                "La incidencia debe ser analizada antes de "
                "confirmar su generación."
            )

        # -----------------------------------------------------
        # 2. VALIDAR DECISIÓN DEL ASESOR
        # -----------------------------------------------------

        if self.classification_decision == "pending":
            raise UserError(
                "Debe revisar la recomendación del ITSM Copilot "
                "antes de confirmar la generación de la incidencia."
            )

        # -----------------------------------------------------
        # 3. VALIDAR EVIDENCIA OBLIGATORIA
        # -----------------------------------------------------

        if not self.evidence_ids:
            raise UserError(
                "Debe adjuntar evidencia donde se visualice el error presentado "
                "antes de confirmar la generación de la incidencia."
            )

        # -----------------------------------------------------
        # 4. GENERAR DEFINITIVAMENTE EL TICKET
        # -----------------------------------------------------

        return self._finalize_incident_creation()

###################################################################################

    def action_keep_classification(self):
        """
        Conserva la clasificación seleccionada originalmente.
        Registra la decisión del Asesor CAC, pero NO genera todavía
        el número INC.
        El asesor deberá revisar la información y confirmar
        posteriormente la generación de la incidencia.
        """

        self.ensure_one()

        # Guarda el proceso seleccionado originalmente.
        original_process = self.process_id.name

        

        # Registra que el asesor decidió mantener su selección.
        self.classification_decision = "maintained"

        # La recomendación continúa existiendo, pero el usuario
        # decide no aplicarla.
        self.reclassification_reason = (
            f"El Asesor CAC decidió mantener la clasificación "
            f"«{original_process}», pese a que el ITSM Copilot "
            f"recomienda «{self.suggested_process}». "
            f"Revise la información antes de confirmar la generación."
        )

        # Importante:
        # aquí NO se genera todavía el ticket.
        return True

    def action_generate_incident(self):
        """
        Genera la incidencia cuando la clasificación coincide
        o cuando el motor no identificó una regla aplicable.
        """

        self.ensure_one()

        if self.state != "analyzed":
            raise UserError(
                "La incidencia debe analizarse antes de generarse."
            )

        if self.is_reclassified:
            raise UserError(
                "Debe aceptar la recomendación o mantener "
                "la clasificación original."
            )

        return self._finalize_incident_creation()

    # ---------------------------------------------------------
    # GENERACIÓN DEL NÚMERO INC
    # ---------------------------------------------------------

    def _finalize_incident_creation(self):
        """
        Asigna el número INC, registra la fecha y cambia el estado.
        """

        self.ensure_one()

        if self.name == "Nuevo":
            self.name = (
                self.env["ir.sequence"].next_by_code(
                    "incident.ticket"
                )
                or "Nuevo"
            )

        if self.name == "Nuevo":
            raise UserError(
                "No fue posible generar el número de incidencia. "
                "Revise la configuración de la secuencia."
            )


         # Busca y asigna el equipo resolutor.
        recommended_team = self.env["incident.team"].search(
            [
                ("name", "=ilike", self.suggested_group),
                ("active", "=", True),
            ],
            limit=1,
        )

        if recommended_team:
            self.assigned_team_id = recommended_team
            self.assigned_date = fields.Datetime.now()

        self.state = "created"
        self.generation_date = fields.Datetime.now()

        # Continúa aquí la redirección a Mis incidencias.




        # -----------------------------------------------------
        # REDIRECCIONAR A "MIS INCIDENCIAS"
        # -----------------------------------------------------
        # Recupera la acción definida en la vista XML para mostrar
        # únicamente las incidencias creadas por el usuario actual.
        action = self.env.ref(
            "incident_management.action_my_incident_tickets"
             ).read()[0]

        action["target"] = "current"

        return action

    # ---------------------------------------------------------
    # FUNCIONES AUXILIARES
    # ---------------------------------------------------------

    def _normalize_text(self, text):
        """
        Reutiliza el normalizador del motor inteligente.
        """

        return self.env[
            "classification.engine"
        ].normalize_text(text or "")

    def _find_record_by_normalized_name(
        self,
        model_name,
        expected_name,
        extra_domain=None,
    ):
        """
        Busca un catálogo comparando nombres normalizados.

        Esto permite reconocer, por ejemplo:

        'Reposición de SIM'
        'REPOSICION DE SIM'
        """

        if not expected_name:
            return False

        domain = list(extra_domain or [])
        domain.append(("active", "=", True))

        records = self.env[model_name].search(domain)

        expected_normalized = self._normalize_text(expected_name)

        for record in records:
            if self._normalize_text(record.name) == expected_normalized:
                return record

        return False