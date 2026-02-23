from girder.plugin import GirderPlugin

import girder_plugin


class MedGemmaGirderPlugin(GirderPlugin):
    DISPLAY_NAME = "MedGemma"
    CLIENT_SOURCE_PATH = "web_client"

    def load(self, info):
        girder_plugin.load(info)
