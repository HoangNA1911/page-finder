import os, shutil
os.environ.update({
    "LLM_MODEL":"dummy","LLM_BASE_URL":"http://localhost","LLM_API_KEY":"dummy",
    "PAGEFINDER_SOURCE_MODE":"markdown","PAGEFINDER_DOCS_DIR":"docs",
    "PAGEFINDER_DATA_DIR":".pagefinder_inspect",
})
shutil.rmtree(".pagefinder_inspect", ignore_errors=True)
from pagefinder.service import PagefinderService
s = PagefinderService()
s.sync_pages(force=True)
print("pages:", s.store.count_pages())
