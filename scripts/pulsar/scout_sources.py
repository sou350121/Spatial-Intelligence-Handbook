"""qwen scout fleet — discover high-quality information sources for the Spatial handbook.

16 parallel scouts, each a NATIVE-endpoint qwen call with web search (returns real source
URLs). Each scout covers a distinct discovery angle. Output: /tmp/scout_results.json with
candidate sources + the mechanically-returned search URLs (for grounding).
"""
import json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

NATIVE = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
KEY = __import__("os").environ["DASHSCOPE_API_KEY"]
MODEL = "qwen-plus"

COMMON = """你是 Spatial Intelligence（空间智能：SLAM/VIO/3D重建/NeRF/3DGS/深度估计/feed-forward 3D(DUSt3R/VGGT类)/VLA/世界模型/位姿/追踪/传感器/空间推理；无人机 aerial/drone 是 anchor embodiment）研究的**信息源侦察员**。
用联网搜索找出下面这个角度里**最高质量、当前活跃**的信息源。只列**真实存在、你在搜索结果里确认过**的源；**绝不编造 URL**。优先有 RSS/Atom feed 的源。
严格 JSON 输出（不要多余文字）:
{"sources":[{"name":"...","homepage":"https://...","feed_url":"https://...RSS地址 或 null","type":"lab-blog|researcher|conference|journal|github|industry|newsletter|aggregator|arxiv-category","subfield":"slam|3dgs-nerf|depth|feedforward3d|vla-worldmodel|sensors|aerial|general","quality_reason":"为什么高质量,一句话","language":"en|zh"}]}
目标角度："""

ANGLES = [
    "顶级 3D 视觉 / 神经渲染研究实验室（做 NeRF / 3DGS / feed-forward 3D / 可微渲染的组）的博客 / 新闻 / 项目聚合页及其 RSS",
    "顶级 SLAM / VIO / 视觉惯性状态估计 研究组（如 TUM / ETH ASL / HKUST Aerial Robotics / UZH RPG 类）的信息源与 RSS",
    "顶级机器人感知 / VLA / 世界模型 研究实验室（学术+工业研究院）的博客 / feed",
    "活跃的**个人研究者**技术博客（专写 3DGS / SLAM / world model / feed-forward 3D 深度技术内容的人），要有 RSS",
    "顶会的论文 RSS / 聚合: CVPR / ICCV / ECCV / CoRL / RSS(Robotics Sci&Sys) / ICRA / IROS —— 有没有可订阅的 proceedings/accepted-papers feed",
    "顶刊 RSS: Science Robotics / IEEE T-RO / IJRR / IEEE RA-L / TPAMI / IEEE Robotics & Automation Magazine 的官方 RSS 地址",
    "GitHub 高信号源: spatial AI / SLAM / 3DGS / NeRF / feed-forward-3D 的 awesome-list、以及重要 org（如 nerfstudio / gaussian-splatting 生态）的 release/commits RSS",
    "产业技术博客: NVIDIA (Isaac / Robotics research) / Meta AI (Reality Labs, FAIR) / Google DeepMind / Wayve / World Labs / Skydio 等在空间智能上的技术博客与 RSS",
    "**无人机 / UAV / aerial 空中感知与自主**（anchor embodiment）的最佳信息源: 顶级 aerial robotics 组、竞赛、期刊专栏",
    "空间智能相关**传感器**（事件相机 event camera / LiDAR / 4D radar / 触觉 tactile / 偏振）的最佳研究信息源与社区",
    "**深度估计 / 立体 / MVS / 单目度量深度**（Depth Anything / Metric3D / MoGe 生态）方向的最佳信息源",
    "专门的 3D vision / robotics / spatial-AI **newsletter 与聚合器**（arxiv-sanity、paperswithcode、Deep Learning Monitor、AK/Hugging Face daily papers 类）",
    "**中文高质量源**: 微信公众号 / 知乎专栏 / 机器之心 / 极市平台 等做 3D 视觉、SLAM、机器人、具身智能深度内容的，最好能找到可抓取入口",
    "**arxiv category 审计**: 一个覆盖 SLAM/3DGS/NeRF/depth/VLA/world-model 的空间智能 handbook，除了 cs.RO/cs.CV/cs.AI/cs.LG，还应该监控哪些 arxiv 类别（cs.GR 图形学？eess.IV 图像处理？cs.MM？eess.SP？）——给出类别代码和对应 rss listing URL（http://export.arxiv.org/rss/<cat>）",
    "**世界模型 / generative 3D / embodied simulation**（Cosmos / Genie / GAIA / Aether / World Labs 类）方向的最佳信息源与追踪页",
    "顶级空间智能研究者**实际在读/在追**的高信号源: 有没有 X/Twitter 的 RSS 桥接、Google Scholar alert 替代、Semantic Scholar feed、或高质量 Substack",
]


def scout(i, angle):
    body = {"model": MODEL, "input": {"messages": [{"role": "user", "content": COMMON + angle}]},
            "parameters": {"result_format": "message", "temperature": 0.3, "max_tokens": 2000,
                           "enable_search": True,
                           "search_options": {"forced_search": True, "enable_source": True,
                                              "enable_citation": True, "search_strategy": "turbo"}}}
    req = urllib.request.Request(NATIVE, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=120))
            break
        except Exception as e:
            if attempt == 2:
                return {"angle": angle, "error": str(e), "sources": [], "search_urls": []}
    text = (data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content")
            or data.get("output", {}).get("text") or "")
    search_urls = [r.get("url", "") for r in data.get("output", {}).get("search_info", {}).get("search_results", [])]
    m = re.search(r"\{.*\}", text, re.S)
    sources = []
    if m:
        try:
            sources = json.loads(m.group(0)).get("sources", [])
        except Exception:
            pass
    return {"idx": i, "angle": angle[:50], "n": len(sources), "sources": sources,
            "search_urls": [u for u in search_urls if u]}


with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(lambda t: scout(*t), enumerate(ANGLES)))

json.dump(results, open("/tmp/scout_results.json", "w"), ensure_ascii=False, indent=2)
total = sum(len(r["sources"]) for r in results)
print(f"{len(results)} scouts done, {total} candidate sources")
for r in results:
    tag = f"ERR {r.get('error','')[:40]}" if r.get("error") else f"{r['n']} sources, {len(r['search_urls'])} search-urls"
    print(f"  [{r.get('idx','?'):2}] {r['angle']:52} → {tag}")
