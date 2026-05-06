# Troubleshooting

Common issues and solutions for DClaw Agent.

## Quick Diagnostics

```bash
# Check app pods
kubectl get pods -n dclaw-agent

# Check logs
kubectl logs -n dclaw-agent deployment/dclaw-agent-backend

# Check database
kubectl get clusters -n dclaw-agent
```

## Sections

- [Common Issues](./common-issues)
- [FAQ](./faq)
