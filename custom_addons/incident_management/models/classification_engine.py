"""
=============================================================
MOTOR INTELIGENTE DE CLASIFICACIÓN
=============================================================

Este componente constituye el núcleo de la solución.

Responsabilidades:

1. Recibir la descripción de la incidencia.
2. Normalizar el texto ingresado.
3. Consultar las reglas activas de la base de conocimiento.
4. Comparar las palabras o frases configuradas.
5. Calcular un puntaje por coincidencias.
6. Seleccionar la regla con mayor puntaje.
7. Devolver la recomendación al ticket.

Este modelo es AbstractModel porque contiene lógica reutilizable,
pero no genera una tabla propia en PostgreSQL.
=============================================================
"""

# Librería para trabajar con expresiones regulares.
import re

# Librería para normalizar caracteres y eliminar tildes.
import unicodedata

# Importamos el componente models del framework Odoo.
from odoo import models


class ClassificationEngine(models.AbstractModel):
    """
    Motor encargado de analizar las descripciones de las incidencias.
    """

    # Nombre técnico con el que otros modelos llaman al motor.
    _name = "classification.engine"

    # Descripción funcional del componente.
    _description = "Motor Inteligente de Clasificación"

    # --------------------------------------------------------
    # NORMALIZACIÓN DEL TEXTO
    # --------------------------------------------------------

    def normalize_text(self, text):
        """
        Convierte un texto a una forma uniforme para facilitar
        su comparación.

        Ejemplo:

        Entrada:
        'No se Activó el ICCID.'

        Salida:
        'no se activo el iccid'
        """

        # Si el texto está vacío, devuelve una cadena vacía.
        if not text:
            return ""

        # Convierte todo el texto a minúsculas.
        text = text.lower()

        # Separa las letras de sus signos diacríticos.
        # Por ejemplo: "ó" se separa en "o" + tilde.
        text = unicodedata.normalize("NFKD", text)

        # Elimina las tildes y otros signos diacríticos.
        text = "".join(
            character
            for character in text
            if not unicodedata.combining(character)
        )

        # Reemplaza signos de puntuación por espacios.
        text = re.sub(r"[^\w\s]", " ", text)

        # Reemplaza múltiples espacios por uno solo.
        text = re.sub(r"\s+", " ", text)

        # Elimina espacios al inicio y al final.
        return text.strip()

    # --------------------------------------------------------
    # CONSULTA DE REGLAS
    # --------------------------------------------------------

    def get_rules(self):
        """
        Obtiene las reglas activas registradas en Odoo.

        La información se recupera desde el modelo incident.rule,
        que representa la base de conocimiento del sistema.
        """

        return self.env["incident.rule"].search([
            ("active", "=", True)
        ])

    # --------------------------------------------------------
    # OBTENCIÓN DE PALABRAS CLAVE
    # --------------------------------------------------------

    def get_valid_keywords(self, rule):
        """
        Convierte el campo de palabras clave de una regla en una lista.

        Ejemplo:

        'reposicion, chip, sim, iccid'

        se transforma en:

        ['reposicion', 'chip', 'sim', 'iccid']
        """

        # Si no existen palabras clave, devuelve una lista vacía.
        if not rule.keywords:
            return []

        # Divide el texto utilizando la coma como separador.
        raw_keywords = rule.keywords.split(",")

        # Lista donde se almacenarán las palabras normalizadas.
        valid_keywords = []

        # Recorre las palabras ingresadas en la regla.
        for raw_keyword in raw_keywords:

            # Normaliza cada palabra o frase.
            keyword = self.normalize_text(raw_keyword)

            # Solo guarda valores que no estén vacíos.
            if keyword:
                valid_keywords.append(keyword)

        return valid_keywords

    # --------------------------------------------------------
    # CÁLCULO DEL PUNTAJE
    # --------------------------------------------------------

    def calculate_score(self, text, rule):
        """
        Compara el texto normalizado con las palabras clave de una regla.

        Retorna dos valores:

        score:
            Puntaje total obtenido por la regla.

        matches:
            Palabras o frases que coincidieron con la descripción.
        """

        # Puntaje inicial.
        score = 0

        # Lista de coincidencias encontradas.
        matches = []

        # Obtiene las palabras clave válidas de la regla.
        keywords = self.get_valid_keywords(rule)

        # Recorre cada palabra o frase configurada.
        for keyword in keywords:

            # Variable que indica si existe coincidencia.
            is_match = False

            # Si el tipo es coincidencia exacta,
            # todo el texto debe ser igual al patrón configurado.
            if rule.match_type == "exact":
                is_match = text == keyword

            # En el tipo "Contiene", basta con que el patrón
            # aparezca dentro de la descripción.
            else:
                is_match = keyword in text

            # Si existe coincidencia, se suma el peso de la regla.
            if is_match:

                # Si el peso fuese cero o estuviera vacío,
                # se utiliza 1 como valor mínimo.
                score += rule.weight or 1

                # Registra el patrón que generó la coincidencia.
                matches.append(keyword)

        return score, matches

    # --------------------------------------------------------
    # ANÁLISIS PRINCIPAL
    # --------------------------------------------------------

    def analyze(self, description):
        """
        Método principal del motor.

        Recibe la descripción de la incidencia y devuelve un
        diccionario con la recomendación generada.
        """

        # Normaliza la descripción ingresada por el usuario.
        text = self.normalize_text(description)

        # Si la descripción está vacía, no se realiza el análisis.
        if not text:
            return self.build_empty_result()

        # Obtiene todas las reglas activas.
        rules = self.get_rules()

        # Variable que almacenará la mejor regla.
        best_rule = None

        # Mayor puntaje encontrado.
        best_score = 0

        # Coincidencias de la mejor regla.
        best_matches = []

        # Recorre todas las reglas activas.
        for rule in rules:

            # Calcula el puntaje de la regla actual.
            score, matches = self.calculate_score(text, rule)

            # Si el puntaje supera al mejor resultado anterior,
            # esta regla pasa a ser la mejor candidata.
            if score > best_score:
                best_rule = rule
                best_score = score
                best_matches = matches

        # Si ninguna regla obtuvo coincidencias,
        # se devuelve un resultado vacío y controlado.
        if not best_rule:
            return self.build_empty_result()

        # Obtiene únicamente las palabras clave válidas.
        valid_keywords = self.get_valid_keywords(best_rule)

        # Calcula la confianza según la proporción de patrones encontrados.
        if valid_keywords:
            confidence = round(
                (len(best_matches) / len(valid_keywords)) * 100,
                2
            )
        else:
            confidence = 0

        # Devuelve la recomendación generada.
        return {
            "process": best_rule.suggested_process or "",
            "application": best_rule.suggested_application or "",
            "scenario": best_rule.suggested_scenario or "",
            "group": best_rule.suggested_group or "",
            "confidence": confidence,
            "score": best_score,
            "matches": best_matches,
            "rule_name": best_rule.name or "",
        }

    # --------------------------------------------------------
    # RESULTADO SIN COINCIDENCIA
    # --------------------------------------------------------

    def build_empty_result(self):
        """
        Genera una respuesta estándar cuando el motor no encuentra
        una regla compatible con la descripción.
        """

        return {
            "process": "",
            "application": "",
            "scenario": "",
            "group": "",
            "confidence": 0,
            "score": 0,
            "matches": [],
            "rule_name": "",
        }