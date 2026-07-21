"""Round-2 qwen scout wave — hunt MACHINE-READABLE feeds we can actually ingest.
Focus: top GitHub repos (→ releases.atom, high-signal) + industry/newsletter/aggregator RSS.
24 scouts. Each returns repos (owner/name) and/or feeds (url)."""
import json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

NATIVE = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
KEY = os.environ["DASHSCOPE_API_KEY"]
MODEL = "qwen-plus"

COMMON = """你是 Spatial Intelligence（空间智能:SLAM/VIO/3D重建/NeRF/3DGS/深度/feed-forward 3D(DUSt3R/VGGT)/VLA/世界模型/位姿/传感器/空间推理;无人机 aerial 是 anchor）研究的**可订阅信息源侦察员**。目标是找**机器可读、能自动抓取**的源。用联网搜索。**只列真实存在的**,绝不编造。
严格 JSON:
{"repos":[{"owner_repo":"owner/name","subfield":"slam|3dgs-nerf|depth|feedforward3d|vla-worldmodel|sensors|aerial|general","why":"为什么重要/活跃,一句话"}],
 "feeds":[{"name":"...","feed_url":"https://...真实RSS/Atom地址","type":"industry|newsletter|aggregator|lab|community","why":"..."}]}
repos 要给**当前最重要、最活跃、会持续发布 release/更新**的 GitHub 仓库(owner/name 精确)。feeds 只给你确认有 RSS/Atom 的。
角度:"""

ANGLES = [
    "SLAM / VIO / 视觉惯性里程计 最重要最活跃的 GitHub 仓库(如 ORB-SLAM3 / VINS / DPVO / 各家 3DGS-SLAM),要会持续 release 的",
    "3DGS / Gaussian Splatting 生态最核心的 GitHub 仓库(原始 3DGS、加速、SLAM 化、压缩、动态、大规模)",
    "NeRF / neural rendering / 可微渲染 最重要的 GitHub 仓库(nerfstudio、instant-ngp、各家 NeRF 变体)",
    "feed-forward 3D (DUSt3R / MASt3R / VGGT / Fast3R / MapAnything / π3 / Spann3r) 及其生态的 GitHub 仓库",
    "单目/度量深度估计 最重要的 GitHub 仓库(Depth Anything v1/v2/v3、Metric3D、MoGe、UniDepth、Marigold)",
    "VLA / 世界模型 / 具身 最活跃的开源 GitHub 仓库(π0/openpi、LeRobot、GR00T、Cosmos、Genie 复现、RoboVerse)",
    "空间感知传感器(事件相机 event / LiDAR / 4D radar / 触觉 tactile)最重要的开源仓库与数据集仓库",
    "无人机/UAV 空中自主与感知 最重要的开源仓库(如 Ego-Planner / Fast-Planner / OpenUAV / agile flight)",
    "3D 场景理解 / occupancy / BEV / scene graph 最重要的开源仓库",
    "点云 / 配准 / SfM / MVS 经典与前沿开源仓库(COLMAP / Open3D / GLOMAP / 各家 learned MVS)",
    "机器人学习 / manipulation policy 最活跃的开源框架(会持续 release 的)",
    "3D 生成 / 世界基础模型(World Foundation Model) 开源仓库(Cosmos / Aether / Hunyuan3D / TRELLIS)",
    "产业界空间智能/机器人技术博客**确认有 RSS 的**: NVIDIA / Google DeepMind / Meta AI / Wayve / Waymo / World Labs / Boston Dynamics / Skydio",
    "AI/ML 论文聚合器**确认有 RSS/API 的**: Hugging Face daily papers、Papers with Code、arxiv-sanity、alphaXiv、Semantic Scholar、Cool Papers(papers.cool)",
    "3D 视觉/机器人/具身智能领域**有 RSS 的 Substack / 个人博客 / newsletter**(英文)",
    "顶级机器人/视觉实验室**有 news RSS 或 GitHub org(会 release)**的: ETH ASL/RSL、UZH RPG、TUM、HKUST Aerial、CMU、MIT、Stanford SVL、UPenn GRASP",
    "计算机视觉/图形学社区**有 RSS 的资源**: Two Minute Papers 类、The Gradient、机器学习/视觉 subreddit RSS、arxiv listing 变体",
    "中文空间智能/3D视觉/具身**可抓取入口**: 机器之心 RSS、量子位、极市、PaperWeekly、有 RSS 的知乎专栏或公众号镜像(rsshub 类)",
    "SLAM/3D 重建**评测榜单与 benchmark 仓库**(会更新的): KITTI/EuRoC/TUM 榜、Nerf/3DGS benchmark、ScanNet/Replica 相关",
    "点跟踪 / 光流 / 6-DoF 位姿 最重要的开源仓库(CoTracker / TAPIR / FoundationPose / SAM2 in 3D)",
    "神经隐式表面 / SDF / mesh 重建 最重要的开源仓库(NeuS / Neuralangelo / 各家)",
    "自动驾驶感知(与空间智能重叠部分)最活跃的开源仓库(occupancy / BEV / world model for driving)",
    "空间智能相关的 Awesome-list GitHub 仓库(会更新的:awesome-3D-gaussian / awesome-NeRF / awesome-SLAM / awesome-VLA / awesome-depth)",
    "**补漏 scout**: 上面没覆盖但对一个世界级空间智能 handbook 最有价值、且机器可读(RSS/Atom/GitHub release)的信息源还有哪些?",
]


def scout(i, angle):
    body = {"model": MODEL, "input": {"messages": [{"role": "user", "content": COMMON + angle}]},
            "parameters": {"result_format": "message", "temperature": 0.3, "max_tokens": 2200,
                           "enable_search": True,
                           "search_options": {"forced_search": True, "enable_source": True, "search_strategy": "turbo"}}}
    req = urllib.request.Request(NATIVE, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=120)); break
        except Exception as e:
            if attempt == 2:
                return {"idx": i, "angle": angle[:40], "repos": [], "feeds": [], "error": str(e)}
    text = (data.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content") or "")
    m = re.search(r"\{.*\}", text, re.S)
    repos, feeds = [], []
    if m:
        try:
            obj = json.loads(m.group(0)); repos = obj.get("repos", []); feeds = obj.get("feeds", [])
        except Exception:
            pass
    return {"idx": i, "angle": angle[:40], "repos": repos, "feeds": feeds}


with ThreadPoolExecutor(max_workers=6) as ex:
    results = list(ex.map(lambda t: scout(*t), enumerate(ANGLES)))
json.dump(results, open("/tmp/scout_feeds_results.json", "w"), ensure_ascii=False, indent=2)
nr = sum(len(r["repos"]) for r in results); nf = sum(len(r["feeds"]) for r in results)
print(f"{len(results)} scouts done, {nr} repos + {nf} feeds")
for r in results:
    print(f"  [{r['idx']:2}] {r['angle']:42} → {len(r['repos'])} repos, {len(r['feeds'])} feeds"
          + (f" ERR {r.get('error','')[:30]}" if r.get('error') else ""))
