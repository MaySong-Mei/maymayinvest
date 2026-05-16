# maymayinvest

Personal AI-native investment management system.

Iterations live in versioned folders so old designs stay reproducible:

- [`v1/`](v1/) — current iteration. FastAPI + Next.js + Postgres/Timescale, Alpaca paper, AI-native operator surface. See [`v1/docs/ARCHITECTURE.md`](v1/docs/ARCHITECTURE.md).

Scope (all iterations):
1. 连接真实交易 API
2. 回测策略
3. 情报和信息追踪
4. 长短期交易
5. 资产配置和 dashboard 控制
6. 右侧交易（趋势确认追入）
