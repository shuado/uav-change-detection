from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="uav-change-detection",
    version="0.1.0",
    author="东东",
    author_email="shwado@yeah.net",
    description="无人机正射影像图斑级变化检测系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shuado/uav-change-detection",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.0.0",
        "rasterio>=1.3.0",
        "geopandas>=0.13.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "uav-cd-preprocess=src.preprocessing.main:main",
            "uav-cd-train=src.training.main:main",
            "uav-cd-detect=src.inference.main:main",
        ],
    },
)
