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
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/incident_sequence.xml",
        
        "views/incident_ticket_views.xml",
        "views/incident_process_views.xml",
        "views/incident_catalog_views.xml",
        "views/incident_team_views.xml",
        "views/incident_n2_views.xml",
        "views/incident_dashboard_views.xml",
        "views/incident_analysis_views.xml",
        "views/incident_menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}