from setuptools import setup, find_packages


def readme():
    with open("README.rst") as r:
        return r.read()

setup(name="cidr_trie",
      version="3.1.2",
      description="Store/search CIDR prefixes in a trie structure.",
      long_description=readme(),
      long_description_content_type="text/x-rst",
      keywords="cidr ip ipv4 ipv6 trie",
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3 :: Only",
          "Topic :: Internet",
          "Topic :: Software Development :: Libraries :: Python Modules"
      ],
      url="https://github.com/Figglewatts/cidr-trie",
      author="Figglewatts",
      author_email="me@figglewatts.co.uk",
      license="MIT",
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      platforms=["any"])
