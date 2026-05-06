# Frequently Asked Questions

## General

### How do I update DClaw Agent?

Update the `version` field in the DClawApp CRD. The operator will perform a rolling update.

```bash
kubectl patch dclawapp agent --type merge -p '{"spec":{"version":"0.2.0"}}'
```

### How do I back up my data?

Use the `dclaw-backup` app or configure scheduled backups:

```yaml
spec:
  database:
    backups:
      enabled: true
      schedule: "0 2 * * *"
```

### How do I scale the app?

Adjust replicas in the DClawApp CRD:

```yaml
spec:
  frontend:
    replicas: 3
  backend:
    replicas: 3
```

### Can I run DClaw Agent without Kubernetes?

Yes, for local development:

```bash
cd dclaw-agent/frontend && npm run dev
cd dclaw-agent/backend && uvicorn dclaw_agent.main:app --reload
```

## Support

For issues not covered here, check the [DClaw Platform Troubleshooting Guide](../../ecosystem/troubleshooting).
