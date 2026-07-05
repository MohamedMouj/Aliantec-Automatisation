from django.template import Template, Context

template = Template('{{ password_url|default:"../password/" }}')
print(template.render(Context({})))
