def extract_content(response):
    if hasattr(response, "choices"):
        return response.choices[0].message.content

    return response