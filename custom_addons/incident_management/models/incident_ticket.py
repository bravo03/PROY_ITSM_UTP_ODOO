# Herramientas principales del framework Odoo.
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import timedelta


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

    # Analista que tomó la incidencia para su atención.
    assigned_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Analista asignado",
        readonly=True,
        ondelete="set null",
    )

    # Fecha y hora en que el analista inició la atención.
    attention_date = fields.Datetime(
        string="Fecha de inicio de atención",
        readonly=True,
    )

    # Fecha y hora en que la incidencia fue resuelta.
    resolved_date = fields.Datetime(
        string="Fecha de resolución",
        readonly=True,
    )

    # cierre de la incidencia
    closed_date = fields.Datetime(
        string="Fecha de cierre",
        readonly=True,
    )

    # Detalle de la solución aplicada por el analista.
    resolution_notes = fields.Text(
        string="Detalle de resolución",
    )

    priority = fields.Selection(
        [
            ("critical", "CRÍTICA"),
        ],
        string="Prioridad",
        default="critical",
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
            ("in_progress", "En atención"),
            ("resolved", "Resuelto"),
            ("closed", "Cerrado"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
    )

    # ---------------------------------------------------------
    # GESTIÓN DE SLA
    # ---------------------------------------------------------

    sla_target_minutes = fields.Integer(
        string="SLA objetivo (min)",
        default=60,
        readonly=True,
        help="Tiempo objetivo configurado para la atención de la incidencia.",
    )

    sla_deadline = fields.Datetime(
        string="Fecha límite SLA",
        compute="_compute_sla_deadline",
        store=True,
    )

    sla_status = fields.Selection(
        [
            ("on_time", "En tiempo"),
            ("warning", "Próximo a vencer"),
            ("breached", "SLA vencido"),
            ("met", "SLA cumplido"),
        ],
        string="Estado SLA",
        compute="_compute_sla_status",
        store=False,
    )

    sla_resolution_minutes = fields.Float(
        string="Tiempo consumido SLA (min)",
        compute="_compute_sla_status",
        store=False,
        digits=(16, 2),
    )

    # -------------------------------------------------------------------------------

    @api.depends(
        "generation_date",
        "sla_target_minutes",
    )
    def _compute_sla_deadline(self):
        """
        Calcula la fecha límite del SLA a partir de la fecha
        de generación de la incidencia y el objetivo definido.
        """

        for ticket in self:

            if ticket.generation_date and ticket.sla_target_minutes:
                ticket.sla_deadline = ticket.generation_date + timedelta(
                    minutes=ticket.sla_target_minutes
                )
            else:
                ticket.sla_deadline = False

    # ---------------------------------------------------------------------------

    @api.depends(
        "generation_date",
        "resolved_date",
        "state",
        "sla_deadline",
        "sla_target_minutes",
    )
    def _compute_sla_status(self):
        """
        Calcula dinámicamente el tiempo consumido y
        el estado actual del SLA.
        """

        now = fields.Datetime.now()

        for ticket in self:

            ticket.sla_resolution_minutes = 0
            ticket.sla_status = "on_time"

            if not ticket.generation_date or not ticket.sla_deadline:
                continue

            # Si está resuelto usamos la fecha de resolución.
            # Si continúa abierto usamos la hora actual.
            reference_date = ticket.resolved_date if ticket.resolved_date else now

            elapsed_minutes = (
                reference_date - ticket.generation_date
            ).total_seconds() / 60

            ticket.sla_resolution_minutes = max(
                elapsed_minutes,
                0,
            )

            # ---------------------------------------------
            # INCIDENCIA RESUELTA
            # ---------------------------------------------

            if ticket.resolved_date:

                if ticket.resolved_date <= ticket.sla_deadline:
                    ticket.sla_status = "met"
                else:
                    ticket.sla_status = "breached"
                continue

            # ---------------------------------------------
            # INCIDENCIA ABIERTA
            # ---------------------------------------------

            remaining_minutes = (ticket.sla_deadline - now).total_seconds() / 60
            if remaining_minutes < 0:
                ticket.sla_status = "breached"
            elif remaining_minutes <= (ticket.sla_target_minutes * 0.20):
                ticket.sla_status = "warning"
            else:
                ticket.sla_status = "on_time"

    # ---------------------------------------------------------------------------

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
                "Estimado usuario, adjunte evidencia donde se visualice "
                "el error que impide continuar con el proceso."
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
                ticket.matched_patterns = "No se encontraron patrones coincidentes."

            # Obtiene los procesos para compararlos.
            selected_process = self._normalize_text(ticket.process_id.name)

            suggested_process = self._normalize_text(ticket.suggested_process)

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
            raise UserError("No existe una recomendación que pueda aplicarse.")

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
            summary_domain.append(("application_id", "=", recommended_application.id))

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
                "La incidencia debe ser analizada antes de " "confirmar su generación."
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
                "Estimado usuario, adjunte evidencia donde se visualice el error que impide continuar con el proceso."
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

    # ---------------------------------------------------------
    # OPERACIÓN DEL EQUIPO RESOLUTOR
    # ---------------------------------------------------------

    def action_take_incident(self):
        """
        Permite que el analista actual tome la incidencia.

        Registra al usuario responsable y cambia el estado
        de la incidencia a Asignado.
        """

        self.ensure_one()

        if self.state != "created":
            raise UserError(
                "Solo pueden tomarse incidencias que se encuentren "
                "en estado Incidencia generada."
            )

        self.assigned_user_id = self.env.user
        self.assigned_date = fields.Datetime.now()
        self.state = "assigned"

        return True

    def action_start_attention(self):
        """
        Registra el inicio efectivo de la atención técnica.
        """

        self.ensure_one()

        if self.state != "assigned":
            raise UserError(
                "La incidencia debe estar asignada antes de iniciar " "su atención."
            )

        if self.assigned_user_id != self.env.user:
            raise UserError("Solo el analista asignado puede iniciar la atención.")

        self.attention_date = fields.Datetime.now()
        self.state = "in_progress"

        return True

    def action_resolve_incident(self):
        """
        Marca la incidencia como resuelta.

        Exige que el analista haya registrado el detalle
        de la solución aplicada.
        """

        self.ensure_one()

        if self.state != "in_progress":
            raise UserError(
                "La incidencia debe encontrarse en atención " "antes de ser resuelta."
            )

        if self.assigned_user_id != self.env.user:
            raise UserError("Solo el analista asignado puede resolver la incidencia.")

        if not self.resolution_notes:
            raise UserError(
                "Debe registrar el detalle de la solución aplicada "
                "antes de resolver la incidencia."
            )

        self.resolved_date = fields.Datetime.now()
        self.state = "resolved"

        return True

    def action_close_incident(self):
        """
        Cierra definitivamente una incidencia resuelta.

        Solo permite el cierre cuando el ticket se encuentra
        en estado Resuelto.
        """

        self.ensure_one()

        if self.state != "resolved":
            raise UserError(
                "Solo pueden cerrarse incidencias que se encuentren "
                "en estado Resuelto."
            )

        self.closed_date = fields.Datetime.now()
        self.state = "closed"

        return True

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
                self.env["ir.sequence"].next_by_code("incident.ticket") or "Nuevo"
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

        # --------------------------------------------------

        # -----------------------------------------------------
        # REDIRECCIONAR A "MIS INCIDENCIAS"
        # -----------------------------------------------------
        # Recupera la acción definida en la vista XML para mostrar
        # únicamente las incidencias creadas por el usuario actual.
        action = self.env.ref("incident_management.action_my_incident_tickets").read()[
            0
        ]
        action["target"] = "current"
        return action

    # ---------------------------------------------------------
    # FUNCIONES AUXILIARES
    # ---------------------------------------------------------

    def _normalize_text(self, text):
        """
        Reutiliza el normalizador del motor inteligente.
        """
        return self.env["classification.engine"].normalize_text(text or "")

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
