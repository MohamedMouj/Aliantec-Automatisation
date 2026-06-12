from django.shortcuts import render


def index(request):
    """Main landing page for Listes_Types app with list-type selection."""
    list_type_options = [
        {
            "value": "fenetrage",
            "label": "Fenetrage",
            "description": "Fenetrage list-type synchronization and updates.",
            "url": "/listes_types/fenetrage/"
        },
        {
            "value": "dad_dag",
            "label": "DAD_DAG",
            "description": "DAD_DAG list-type processing and reconciliation.",
            "url": "/listes_types/dad_dag/"
        },
        {
            "value": "project_project",
            "label": "Project Project",
            "description": "Project Project list-type management and updates.",
            "url": "/listes_types/projet_project/"
        },
    ]
    
    context = {
        'list_type_options': list_type_options,
    }
    return render(request, 'Listes_Types/index.html', context)
