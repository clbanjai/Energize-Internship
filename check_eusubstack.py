from newsletter import get_new_eusubstack

new_links = get_new_eusubstack(update=False)
if new_links:
    print("::set-output name=need_tesseract::true")
else:
    print("::set-output name=need_tesseract::false")