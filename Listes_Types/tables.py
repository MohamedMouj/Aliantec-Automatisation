import django_tables2 as tables
from django.utils.html import format_html

class UpdateTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="No.", attrs={"td": {"class": "row-number-cell"}})
    source_xml = tables.Column(verbose_name="Source File", accessor="source_xml")
    current_xml_reference = tables.Column(verbose_name="Current Listes-Types Ref", accessor="current_xml_reference")
    exists_in_excel = tables.Column(verbose_name="Exists in PTA", accessor="exists_in_excel")
    excel_matched_sheet = tables.Column(verbose_name="PTA Sheet", accessor="excel_matched_sheet")
    excel_matched_cell = tables.Column(verbose_name="PTA Cell", accessor="excel_matched_cell")
    new_reference_found = tables.Column(verbose_name="New Reference Detected", accessor="new_reference_found")
    chosen_reference_for_folder_search = tables.Column(verbose_name="Chosen Search Ref", accessor="chosen_reference_for_folder_search")
    neighbor_source_cell = tables.Column(verbose_name="Excel Source Cell", accessor="neighbor_source_cell")
    neighbor_distance = tables.Column(verbose_name="Neighbor Distance", accessor="neighbor_distance")
    file_found_in_folder = tables.Column(verbose_name="File Found", accessor="file_found_in_folder")
    xml_updated = tables.Column(verbose_name="Listes-Types Updated", accessor="xml_updated")
    old_xml_ref_value = tables.Column(verbose_name="Old Listes-Types Ref Value", accessor="old_xml_ref_value")
    new_xml_ref_value = tables.Column(verbose_name="New Listes-Types Ref Value", accessor="new_xml_ref_value")
    status = tables.Column(verbose_name="Status", accessor="status")
    reason = tables.Column(verbose_name="Reason", accessor="reason")

    def render_status(self, value):
        color = "black"
        if any(keyword in value for keyword in ["UPDATED", "FILE_FOUND", "OK"]):
            color = "darkgreen"
        elif any(keyword in value for keyword in ["NOT_FOUND", "FILE_NOT_FOUND"]):
            color = "red"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, value)

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False

class AdditionTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="No.", attrs={"td": {"class": "row-number-cell"}})
    file_found = tables.Column(verbose_name="File Found", accessor="file_found")
    ref = tables.Column(verbose_name="Ref Value", accessor="ref")
    action = tables.Column(verbose_name="Add to Listes-Types?", accessor="action")

    def render_action(self, value):
        return format_html('<button type="button" class="btn-submit" style="padding: 8px 15px; width: auto; margin: 0; font-size: 0.9rem;">{}</button>', value)

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False

class DeletionTable(tables.Table):
    row_number = tables.TemplateColumn(template_code=" ", orderable=False, verbose_name="No.", attrs={"td": {"class": "row-number-cell"}})
    source_xml = tables.Column(verbose_name="Source File", accessor="source_xml")
    file_found = tables.Column(verbose_name="File Found", accessor="file_found")
    ref = tables.Column(verbose_name="Listes-Types Ref Value", accessor="ref")
    action = tables.Column(verbose_name="Delete from Listes-Types", accessor="action")

    class Meta:
        attrs = {"class": "table table-striped table-hover"}
        orderable = False
