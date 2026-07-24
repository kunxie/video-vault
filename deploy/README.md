# Deployment package

This directory is the application-owned deployment contract consumed by the
`macmini-lab` personal application registry. The platform checks out an exact
Video Vault commit and replaces the symbolic runtime and migration images with
reviewed, immutable GHCR digests.

The package exposes the web UI only through a private Tailscale Ingress. It
owns the Deployment, Service, migration and verification hooks, resource
limits, probes, and default-deny network policies. PostgreSQL and MinIO
credentials remain in operator-created Kubernetes Secrets and are never
stored in Git.

Render the package locally with:

```bash
kubectl kustomize deploy/overlays/macmini-lab
```

Merging this repository does not directly change the cluster. Deployment
requires a separate reviewed update to
`macmini-lab/k8s/registry/video-vault/production.json`.
