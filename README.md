# Docling Haystack converter

## Usage

Basic usage in a Haystack pipeline looks as follows:

```python
from haystack import Pipeline
from docling_haystack.converter import DoclingConverter

idx_pipe = Pipeline()
# ...
converter = DoclingConverter()
idx_pipe.add_component("converter", converter)
# ...
```

For end-to-end usage samples check out the [examples](examples/).
