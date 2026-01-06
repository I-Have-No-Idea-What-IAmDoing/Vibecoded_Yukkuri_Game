"""
Render System Module.
"""


from .render_system_new import NewRenderSystem


# Re-exporting NewRenderSystem as RenderSystem for compatibility
class RenderSystem(NewRenderSystem):
    pass
