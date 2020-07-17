# Image embedding tests

Done in python using the following:
```python
import gh_md_to_html

gh_md_to_html.main(
    open("github-flavored-markdown-to-html/docs/image_test_from_string.md", "r").read(),
    origin_type="string",
    destination="github-flavored-markdown-to-html/docs",
    css_paths="github-flavored-markdown-to-html/docs/css",
    output_name="image_test_from_string.html"
)
```

## Image from url:

![image1](https://avatars2.githubusercontent.com/u/31518703?s=460&u=b4331e6be145f39b7e48dc39e9b16d7e581e98b3&v=4)

## Image from local file path

(the image is placed within the cwd for this to work)

![image2](github-flavored-markdown-to-html/docs/image_test_from_file.jpeg)

## Image from absolute file path

(the image lies in `/home/phseiff/image_test_from_file.jpeg` and I am using
Ubuntu, obviously)

![image3](/home/philipp/image_test_from_file.jpeg)

Note: It is correctly asked for confirmation before embedding the images from disk.
