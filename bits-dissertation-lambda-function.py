import boto3
import re
import time
import os

def lambda_handler(event, context):
    s3_bucket_name = os.environ["S3_BUCKET_NAME"]
    cf_dist_id = os.environ["CF_DIST_ID"]
    s3_client = boto3.client("s3")
    cf_client = boto3.client("cloudfront")

    # Get CloudFront domain name
    cf_info = cf_client.list_distributions()
    dist_item = [d for d in cf_info["DistributionList"]["Items"] if d["Id"] == cf_dist_id][0]
    cloudfront_url = dist_item["DomainName"]

    # List all image files from S3
    objs = s3_client.list_objects_v2(Bucket=s3_bucket_name)
    image_objs = []
    if "Contents" in objs:
        for obj in objs["Contents"]:
            key = obj["Key"]
            print(key)
            if (re.search(r"\.(jpg|jpeg|png|gif|bmp|webp)$", key, re.IGNORECASE) and key != "favicon.png"):
                url = f"https://{cloudfront_url}/{key}"
                name = os.path.splitext(os.path.basename(key))[0]
                image_objs.append({'url': url, 'name': name})

    # Build JS array for gallery
    js_array = ',\n            '.join(
        [f'{{url: "{img["url"]}", name: "{img["name"]}"}}' for img in image_objs]
    )

    # HTML code for interactive gallery (with modal preview)
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Gallery</title>
        <meta charset="utf-8"/>
        <link rel="icon" href="/favicon.png" type="image/png">
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background: linear-gradient(120deg, #0c0225 0%, #200b98 100%);
            }}
            h1 {{
                text-align: center;
                color: #def7b8;
            }}
            .gallery {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                justify-content: center;
            }}
            .image-block {{
                background-color: #fffbe6;
                border: 2px solid #ffe082;
                padding: 14px 10px 10px 10px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(240,129,15,0.10);
                width: 220px;
                margin-bottom: 12px;
            }}
            .image-frame {{
                width: 200px;
                height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                overflow: hidden;
                background: #f9f9f9;
                margin: 0 auto 8px auto;
                box-shadow: 1px 2px 6px rgba(240,129,15,0.08);
            }}
            .image-frame img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 8px;
                display: block;
            }}
            .download-btn, .view-btn {{
                display: inline-block;
                padding: 6px 14px;
                background: #ffb347;
                color: #fff;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 5px;
                font-size: 14px;
                margin-right: 6px;
                transition: background 0.2s;
                border: none;
                cursor: pointer;
            }}
            .download-btn:hover, .view-btn:hover {{
                background: #fd6e6a;
            }}
            .pagination {{
                text-align: center;
                margin-top: 22px;
            }}
            .pagination button {{
                background: #ffb347;
                border: none;
                color: #fff;
                padding: 8px 14px;
                margin: 0 2px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
                transition: background 0.2s;
            }}
            .pagination button.active,
            .pagination button:hover {{
                background: #fd6e6a;
            }}
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0; top: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0,0,0,0.75);
                justify-content: center;
                align-items: center;
            }}
            .modal-content {{
                position: relative;
                background: #fffbe6;
                padding: 32px 16px 16px 16px;
                border-radius: 14px;
                max-width: 700px;
                width: 90vw;
                max-height: 80vh;
                text-align: center;
                box-shadow: 0 6px 24px rgba(240,129,15,0.14);
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .modal-content img {{
                max-width: 100%;
                max-height: 65vh;
                border-radius: 10px;
                margin-bottom: 12px;
            }}
            .modal-close {{
                position: absolute;
                top: 10px; right: 18px;
                font-size: 32px;
                color: #fd6e6a;
                cursor: pointer;
                border: none;
                background: none;
            }}
            .modal-caption {{
                font-size: 1.1em;
                color: #333;
                margin-bottom: 8px;
            }}
            @media (max-width: 500px) {{
                .image-block, .image-frame {{
                    width: 120px !important;
                    height: 120px !important;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>Static Web Image Gallery</h1>
        <div class="gallery" id="gallery"></div>
        <div class="pagination" id="pagination"></div>

        <!-- Modal for viewing images -->
        <div class="modal" id="modal">
            <div class="modal-content" id="modal-content">
                <button class="modal-close" id="modal-close" title="Close">&times;</button>
                <div class="modal-caption" id="modal-caption"></div>
                <img id="modal-img" src="" alt="">
                <a href="" id="modal-download" download class="download-btn">Download</a>
            </div>
        </div>

        <script>
            

            // Inject image metadata
            const images = [
                {js_array}
            ];

            const IMAGES_PER_PAGE = 12;
            let currentPage = 1;

            function renderGallery() {{
                const gallery = document.getElementById('gallery');
                gallery.innerHTML = '';
                const startIdx = (currentPage - 1) * IMAGES_PER_PAGE;
                const endIdx = startIdx + IMAGES_PER_PAGE;

                images.slice(startIdx, endIdx).forEach((img, idx) => {{
                    gallery.innerHTML += `
                        <div class="image-block">
                            <div class="image-frame">
                                <img src="${{img.url}}" alt="${{img.name}}">
                            </div>
                            <div><strong>${{img.name}}</strong></div>
                            <button class="view-btn" onclick="openModal('${{img.url.replace(/'/g,"\\\\'")}}','${{img.name.replace(/'/g,"\\\\'")}}')">View</button>
                            <a href="${{img.url}}" download class="download-btn">Download</a>
                        </div>
                    `;
                }});
            }}

            function renderPagination() {{
                const pagination = document.getElementById('pagination');
                pagination.innerHTML = '';
                const pageCount = Math.ceil(images.length / IMAGES_PER_PAGE);

                for(let i=1; i<=pageCount; i++) {{
                    pagination.innerHTML += `
                        <button class="${{i === currentPage ? 'active' : ''}}" onclick="goToPage(${{i}})">${{i}}</button>
                    `;
                }}
            }}

            function goToPage(pageNum) {{
                currentPage = pageNum;
                renderGallery();
                renderPagination();
            }}

            function openModal(url, name) {{
                document.getElementById('modal-img').src = url;
                document.getElementById('modal-img').alt = name;
                document.getElementById('modal-caption').textContent = name;
                document.getElementById('modal-download').href = url;
                document.getElementById('modal').style.display = 'flex';
            }}
            function closeModal() {{
                document.getElementById('modal').style.display = 'none';
                document.getElementById('modal-img').src = '';
            }}

            document.getElementById('modal-close').onclick = closeModal;
            document.getElementById('modal').onclick = function(e) {{
                if (e.target === this) closeModal();
            }}
            document.onkeydown = function(e) {{
                if (e.key === 'Escape') closeModal();
            }}

            renderGallery();
            renderPagination();
        </script>
    </body>
    </html>
    """

    # Save and upload HTML file
    with open('/tmp/index.html', 'w') as f:
        f.write(html_code)
    s3_client.upload_file('/tmp/index.html', s3_bucket_name, 'index.html', ExtraArgs={'ContentType': "text/html"})

    # Invalidate CloudFront cache so users see updates immediately
    cf_client.create_invalidation(
        DistributionId=cf_dist_id,
        InvalidationBatch={
            'Paths': {'Quantity': 1, 'Items': ['/*']},
            'CallerReference': str(int(time.time()))
        }
    )

    return {"status": "success", "images_found": len(image_objs)}
