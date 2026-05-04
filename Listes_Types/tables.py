import django_tables2 as tables
from django.utils.html import format_html

class UpdateTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="N°", attrs={"td": {"class": "row-number-cell"}})
    source_xml = tables.Column(verbose_name="Fichier Source", accessor="source_xml")
    current_xml_reference = tables.Column(verbose_name="Réf ListesTypes actuelle", accessor="current_xml_reference")
    exists_in_excel = tables.Column(verbose_name="Existe dans PTA", accessor="exists_in_excel")
    excel_matched_sheet = tables.Column(verbose_name="Feuille PTA", accessor="excel_matched_sheet")
    excel_matched_cell = tables.Column(verbose_name="Cellule PTA", accessor="excel_matched_cell")
    new_left_reference_found = tables.Column(verbose_name="Nouvelle réf gauche", accessor="new_left_reference_found")
    chosen_reference_for_folder_search = tables.Column(verbose_name="Réf recherche choisie", accessor="chosen_reference_for_folder_search")
    left_source_cell = tables.Column(verbose_name="Cellule source gauche", accessor="left_source_cell")
    left_distance = tables.Column(verbose_name="Distance à gauche", accessor="left_distance")
    file_found_in_folder = tables.Column(verbose_name="Fichier trouvé", accessor="file_found_in_folder")
    xml_updated = tables.Column(verbose_name="ListesTypes mis à jour", accessor="xml_updated")
    old_xml_ref_value = tables.Column(verbose_name="Ancienne valeur réf ListesTypes", accessor="old_xml_ref_value")
    new_xml_ref_value = tables.Column(verbose_name="Nouvelle valeur réf ListesTypes", accessor="new_xml_ref_value")
    status = tables.Column(verbose_name="Statut", accessor="status")
    reason = tables.Column(verbose_name="Raison", accessor="reason")

    def render_status(self, value):
        color = "black"
        if any(keyword in value for keyword in ["MIS_À_JOUR", "FICHIER_TROUVÉ", "OK"]):
            color = "darkgreen"
        elif any(keyword in value for keyword in ["NON_TROUVÉ", "FICHIER_NON_TROUVÉ"]):
            color = "red"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, value)

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False

class AdditionTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="N°", attrs={"td": {"class": "row-number-cell"}})
    file_found = tables.Column(verbose_name="Fichier trouvé", accessor="file_found")
    ref = tables.Column(verbose_name="Valeur réf", accessor="ref")
    action = tables.Column(verbose_name="Ajouter dans ListesTypes?", accessor="action")

    def render_action(self, value):
        return format_html('<button type="button" class="btn-submit" style="padding: 8px 15px; width: auto; margin: 0; font-size: 0.9rem;">{}</button>', value)

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False

class DeletionTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="N°", attrs={"td": {"class": "row-number-cell"}})
    source_xml = tables.Column(verbose_name="Fichier Source", accessor="source_xml")
    file_found = tables.Column(verbose_name="Fichier trouvé", accessor="file_found")
    ref = tables.Column(verbose_name="Valeur réf ListesTypes", accessor="ref")
    action = tables.Column(verbose_name="Supprime dans ListesTypes", accessor="action")

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False
