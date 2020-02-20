language: python
python:
  - "2.7"
  - "3.7"
cache: true

build:
  ci:
   - mkdir -p shippable/codecoverage
   - shippable_retry pip install --upgrade pip
   - shippable_retry pip install -r requirements.txt
   - shippable_retry pip install coverage
   - "python setup.py -q develop"
   - coverage run -p tests/acitoolkit_test.py
   - coverage run -p tests/aciphysobject_test.py
   - coverage run -p tests/acitoolkitlib_test.py
  on_success:
   - coverage combine
   - coverage report --include=*acitoolkit*
   - coverage xml -o shippable/codecoverage/coverage.xml --include=*acitoolkit*
