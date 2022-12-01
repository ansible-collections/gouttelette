def jinja2_renderer(template_file, generator, **kwargs):
    templateLoader = jinja2.PackageLoader(generator)
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_file)
    return template.render(kwargs)
