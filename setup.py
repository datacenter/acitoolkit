from setuptools import setup
setup(
    name = "acitoolkit",
    version = "0.1",
    packages = ["acitoolkit"],
    author = "Cisco Systems, Inc.",
    author_email = "acitoolkit@cisco.com",
    url = "http://github.com/datacenter/acitoolkit/",
    license = "http://www.apache.org/licenses/LICENSE-2.0",
    install_requires = ["requests"],
    description = "This library allows basic Cisco ACI APIC configuration.",
)
