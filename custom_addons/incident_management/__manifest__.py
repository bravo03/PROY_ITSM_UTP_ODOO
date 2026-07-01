{
    "name": "Gestión Inteligente de Incidencias",
    "version": "1.0",
    "summary": "Módulo para clasificación, asignación y escalamiento de incidencias basado en ITIL 4",
    "description": """
        Módulo desarrollado sobre Odoo para registrar incidencias,
        analizar la descripción de falla y sugerir proceso, aplicación,
        escenario y grupo resolutor.
    """,
    "author": "Bryan Meza / Eilleen Gonzales",
    "category": "Services/Helpdesk",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/incident_ticket_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}