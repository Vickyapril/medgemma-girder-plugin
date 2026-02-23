from setuptools import find_packages, setup


setup(
    name="medgemma-girder-plugin",
    version="1.0.0",
    description="Girder plugin for MedGemma Airflow integration",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    py_modules=[
        "girder_plugin",
        "airflow_integration",
        "dicom_anonymizer",
        "dicom_processor",
        "main",
        "medgemma_client",
        "zip_processor",
    ],
    include_package_data=True,
    package_data={
        "medgemma_ui_plugin": ["web_client/*"],
    },
    entry_points={
        "girder.plugin": [
            "girder_plugin = medgemma_ui_plugin:MedGemmaGirderPlugin",
        ],
    },
)
