import re
import shutil
import sys


def cdn_to_raw(url):
    # jsdelivr (包括 testingcf.jsdelivr.net)
    m = re.match(
        r"https://(?:cdn\.|testingcf\.)?jsdelivr\.net/gh/([^/]+)/([^/@]+)@([^/]+)/(.*)",
        url,
    )
    if m:
        owner, repo, branch, path = m.groups()
        # 直接替换-cdn为-raw，兼容所有后缀
        path = path.replace("-cdn", "-raw")
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    # fastgit
    m = re.match(r"https://raw\.fastgit\.org/([^/]+)/([^/]+)/([^/]+)/(.*)", url)
    if m:
        owner, repo, branch, path = m.groups()
        path = path.replace("-cdn", "-raw")
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    # github.io
    m = re.match(r"https://([^.]+)\.github\.io/([^/]+)/(.*)", url)
    if m:
        user, repo, path = m.groups()
        path = path.replace("-cdn", "-raw")
        return f"https://raw.githubusercontent.com/{user}/{repo}/main/{path}"
    return url


def raw_to_cdn(url, cdn_type="cdn"):
    # raw.githubusercontent.com
    m = re.match(
        r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)", url
    )
    if m:
        owner, repo, branch, path = m.groups()
        # 直接替换-raw为-cdn，兼容所有后缀
        path = path.replace("-raw", "-cdn")
        # github.io 反向
        if branch == "main":
            return f"https://{owner}.github.io/{repo}/{path}"
        # 使用参数化的 jsdelivr 域名
        return f"https://{cdn_type}.jsdelivr.net/gh/{owner}/{repo}@{branch}/{path}"
    # github.io → jsdelivr
    m = re.match(r"https://([^.]+)\.github\.io/([^/]+)/(.*)", url)
    if m:
        user, repo, path = m.groups()
        path = path.replace("-raw", "-cdn")
        return f"https://{cdn_type}.jsdelivr.net/gh/{user}/{repo}@main/{path}"
    return url


def add_repo_info(filename, repo_info, update_time=None):
    """在文件最上方添加或更新仓库信息和更新时间"""
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    # 移除已有的 repo 信息，避免重复
    content = re.sub(r"^# repo:.*\n?", "", content, flags=re.MULTILINE)
    # 移除已有的 update 信息，避免重复
    content = re.sub(r"^# update:.*\n?", "", content, flags=re.MULTILINE)

    # 构造新的头部信息
    header = ""
    if update_time:
        header += f"# update: {update_time}\n"
    header += f"# repo: {repo_info}\n"

    # 写回文件
    content = header + content
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def process_file(filename, cdn_type="cdn"):
    import os

    if "-cdn" in filename:
        mode = "cdn2raw"
        outname = filename.replace("-cdn", "-raw")
    elif "-raw" in filename:
        mode = "raw2cdn"
        outname = filename.replace("-raw", "-cdn")
    else:
        print("文件名需包含-cdn或-raw")
        return

    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # 更新编辑时间
    update_time = re.search(r"# update: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
    current_time = None
    if update_time:
        from datetime import datetime

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = re.sub(update_time.group(0), f"# update: {current_time}", content)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    # 去除 GitHub 代理前缀
    content = re.sub(r"https://ghproxy\.net/", "", content)
    content = re.sub(r"https://gh-proxy\.org/", "", content)

    if mode == "cdn2raw":
        content = re.sub(
            r"https://(?:cdn\.|testingcf\.)?jsdelivr\.net/gh/[^ \n]+",
            lambda m: cdn_to_raw(m.group()),
            content,
        )
        content = re.sub(
            r"https://raw\.fastgit\.org/[^ \n]+",
            lambda m: cdn_to_raw(m.group()),
            content,
        )
        content = re.sub(
            r"https://[a-zA-Z0-9-]+\.github\.io/[^ \n]+",
            lambda m: cdn_to_raw(m.group()),
            content,
        )
        content = re.sub(
            r"(^|[\s,])(https://raw\.githubusercontent\.com/[^\s]+)",
            lambda m: m.group(1) + "https://gh-proxy.org/" + m.group(2),
            content,
            flags=re.MULTILINE,
        )
    else:
        content = re.sub(
            r"https://raw\.githubusercontent\.com/[^ \n]+",
            lambda m: raw_to_cdn(m.group(), cdn_type),
            content,
        )
        content = re.sub(
            r"https://[a-zA-Z0-9-]+\.github\.io/[^ \n]+",
            lambda m: raw_to_cdn(m.group(), cdn_type),
            content,
        )

    with open(outname, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已生成: {outname}")

    add_repo_info(
        outname, "https://github.com/sinspired/proxy-rules 定制规则", current_time
    )

    # ✅ 动态推导 Sinspired_Rules_*.yaml 文件名
    basename = os.path.basename(outname)
    variant_match = re.match(r"clash-(.+?-)?cdn\.yaml", basename)
    if variant_match:
        variant_part = variant_match.group(1)  # "lite-" / "pro-" / None
        if variant_part:
            # "lite-" → "Lite"，"pro-extra-" → "Pro_Extra"
            variant_str = "_".join(
                p.capitalize() for p in variant_part.rstrip("-").split("-")
            )
            sinspired_name = f"Sinspired_Rules_{variant_str}_CDN.yaml"
        else:
            sinspired_name = "Sinspired_Rules_CDN.yaml"
    else:
        sinspired_name = "Sinspired_Rules_" + basename

    shutil.copy(outname, sinspired_name)
    add_repo_info(
        sinspired_name,
        "https://github.com/sinspired/subs-check-pro 内置规则",
        current_time,
    )
    print(f"已额外生成: {sinspired_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "用法: python convert2cdn.py 文件名 [cdn类型, 默认cdn, 可选值: cdn, testingcf]"
        )
    else:
        cdn_type = sys.argv[2] if len(sys.argv) > 2 else "cdn"
        process_file(sys.argv[1], cdn_type)
