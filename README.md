## Open the use interfaces:

Use separate terminals as needed:

```bash
kubectl -n observability port-forward svc/grafana 3000:3000
kubectl -n observability port-forward svc/victoriametrics 8428:8428
kubectl -n observability port-forward svc/victorialogs 9428:9428
kubectl -n observability port-forward svc/vmalert 8880:8880
kubectl -n observability port-forward svc/alertmanager 9093:9093
```

URLs:
| Component | Local URL | Purpose |
|---|---|---|
| Grafana | http://localhost:3000 | Dashboards and Explore |
| VictoriaMetrics | http://localhost:8428/vmui | DirectPromQL/MetricsQL exploration |
| VictoriaLogs | http://localhost:9428/select/vmui | Direct LogsQL exploration |
| VMAlert | http://localhost:8880 | Rules and alert states |
| Alertmanager | http://localhost:9093 | Active alerts, silences, routing status|

Grafana lab credentials are `admin` / `admin`. Grafana may require a password change on first login. Never use this credential pattern outside a dispoasable local lab.

Verify provisioned data sources:

1. Open Grafana.
2. Go to **Connections -> Data Sources**.
3. Select **VictoriaMetrics** and click **Save & test**.
4. Select **VictoriaLogs** and click **Save & test**.
