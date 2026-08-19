#!/bin/bash
# 部署朋友知识库网页版：wiki → Quartz 构建 → Basic Auth 门禁 → Cloudflare Pages
# 用法: bash ~/pkb/tools/deploy_kb_site.sh
# 依赖: <本仓库>/.env 里的 CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN / KB_SITE_PASSWORD
set -e

QUARTZ=~/quartz-preview
WIKI=<你的库>/wiki
PROJECT=<你的Pages项目名>

set -a; source <本仓库>/.env; set +a
[ -n "$KB_SITE_PASSWORD" ] || { echo "缺 KB_SITE_PASSWORD"; exit 1; }

cd "$QUARTZ"
rm -rf content && cp -r "$WIKI" content
npx quartz build

# Basic Auth 门禁 + 禁止搜索引擎收录（_worker.js 会拦截所有请求）
EXPECTED=$(printf 'kb:%s' "$KB_SITE_PASSWORD" | base64)
cat > public/_worker.js <<WORKER
export default {
  async fetch(request, env) {
    const auth = request.headers.get("Authorization") || "";
    if (auth !== "Basic ${EXPECTED}") {
      return new Response("需要密码 / Password required", {
        status: 401,
        headers: {
          "WWW-Authenticate": 'Basic realm="knowledge base", charset="UTF-8"',
          "X-Robots-Tag": "noindex, nofollow",
        },
      });
    }
    const resp = await env.ASSETS.fetch(request);
    const out = new Response(resp.body, resp);
    out.headers.set("X-Robots-Tag", "noindex, nofollow");
    return out;
  },
};
WORKER

npx wrangler pages deploy public --project-name "$PROJECT" --branch main
echo "✅ https://${PROJECT}.pages.dev  账号: kb  密码: 见 <本仓库>/.env 的 KB_SITE_PASSWORD"
