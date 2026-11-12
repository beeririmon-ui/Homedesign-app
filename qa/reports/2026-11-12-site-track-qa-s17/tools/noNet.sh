# sourced by every QA S17 script: no network. Any proxy-aware tool (npm, npx, wrangler's fetch, update checks) is pointed at
# a closed local port, so an attempt to reach the internet fails at once instead of leaving the machine; local addresses
# (my servers on 127.0.0.1) are exempt. npm runs offline. Metrics and update checks off.
export HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 \
  NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost npm_config_offline=true WRANGLER_SEND_METRICS=false \
  NO_UPDATE_NOTIFIER=1 WRANGLER_UPDATE_CHECK=false PATH=/opt/node22/bin:$PATH
