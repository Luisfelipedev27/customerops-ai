# Prepared AWS deployment — not executed

`ecs.yaml` provisions a Fargate cluster, log group, least-privilege IAM roles, task definition,
and service containing API and worker containers. It is a parameterized starting point, not a
validated live AWS deployment.

## Existing infrastructure required

- VPC and private subnets with appropriate egress/NAT or VPC endpoints.
- HTTPS ALB, certificate, and an attached IP target group on port 8000 with /health/ready.
- PostgreSQL with pgvector, backups/PITR, TLS, and a restricted runtime role.
- Authenticated TLS Redis (`rediss://`) with private network access.
- Immutable ARM64 ECR image URI, preferably pinned by digest.
- Secrets Manager JSON containing DATABASE_URL, REDIS_URL, and OPENAI_API_KEY.
- Database and Redis security groups permitting the task security group.

For a customer-managed KMS key, add narrowly scoped kms:Decrypt permissions to the execution role.

## Procedure

1. Run CI, behavioral evaluations, and real-provider validation. Select a supported model and prices.
2. Build the linux/arm64 image and push it to ECR.
3. Apply migrations in a one-off administrative task before updating the service:
   `uv run --no-sync alembic upgrade head`, with a separate administrative database secret.
4. Provision the restricted runtime role and real users. Do not run fictional seed data in production.
5. Validate the template and prepare a CloudFormation change set with account-specific parameters.
6. Review the change set and costs before execution. Keep PostgreSQL and Redis private.
7. Verify HTTPS login, secure cookies, tenant isolation, worker ingestion, traces, and approval.
8. Configure alarms for 5xx, latency, queue length, restarts, connections, and provider spending.
9. Test backup restoration and rollback to the previous image digest.

Normal application tasks must not receive administrative database credentials. The task role
has no extra AWS permissions because the application currently needs no direct AWS runtime API.
API and worker share one task for this version; split services when independent scaling is justified.
Local Docker checks do not validate account networking, IAM, service capacity, or model availability.
No AWS resources, cloud deployment, or paid services were created by this setup.
