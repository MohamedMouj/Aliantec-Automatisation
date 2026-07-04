class SharedData:
    """
    Holds the context for a single processing request.
    This replaces the global static state to allow concurrent requests.
    """
    def __init__(self):
        self.xml_files = []          # List of absolute paths to XML files
        self.fscfai_files = {}       # Map of reference (str) to full filename
        self.references_by_xml = {}  # Map of XML filename to set of references
        self.all_xml_references = set() # Global set of all references in all XML files
        self.excel_refs_desc = {}        # Map of reference (str) to cell object
        self.old_project = None
        self.new_project = None
