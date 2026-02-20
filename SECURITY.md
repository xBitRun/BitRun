# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | ✅ Active development |

## Reporting a Vulnerability

We take the security of BitRun seriously. If you have discovered a security vulnerability, please report it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

1. **Email**: Send details to security@bitrun.ai (if available)
2. **GitHub Security Advisories**: Use the [Security Advisories](https://github.com/xBitRun/BitRun/security/advisories) feature

### What to Include

Please include the following information in your report:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any proof-of-concept or exploit code
- Your contact information for follow-up

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Development**: Depends on severity
- **Disclosure**: After fix is released

### Disclosure Policy

- We follow responsible disclosure practices
- We request that you do not publicly disclose the vulnerability until a fix is available
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When deploying BitRun:

### Environment Variables

- **NEVER** commit `.env` files to version control
- Use strong, unique passwords for `JWT_SECRET` and `DATA_ENCRYPTION_KEY`
- Rotate secrets periodically

```bash
# Generate secure secrets
openssl rand -base64 32
```

### Database Security

- Use strong passwords for PostgreSQL
- Restrict database access to application servers only
- Enable SSL for database connections in production

### API Keys

- Store API keys encrypted in the database (BitRun handles this automatically)
- Use IP whitelisting on exchange APIs when possible
- Use read-only or limited-permission API keys when feasible

### Network Security

- Enable HTTPS with valid SSL certificates
- Configure firewall to restrict access to necessary ports only (80, 443, 22)
- Use VPN or private network for administrative access

### Monitoring

- Enable Sentry for error tracking
- Monitor logs for suspicious activity
- Set up alerts for unusual trading patterns

## Known Security Considerations

### Exchange API Keys

BitRun stores exchange API keys encrypted with AES-256-GCM. However:

- Ensure `DATA_ENCRYPTION_KEY` is securely generated and stored
- Consider using hardware security modules (HSM) for key management in high-security deployments

### Private Keys (Hyperliquid DEX)

For Hyperliquid integration:

- Private keys are stored encrypted in the database
- Use dedicated trading wallets, not main wallets
- Consider using hardware wallets for large amounts

### Authentication

- JWT tokens expire after 60 minutes (access) / 7 days (refresh)
- Failed login attempts trigger account lockout after 5 failures
- Session tokens are invalidated on logout

## Security Updates

Security updates will be announced via:

- GitHub Security Advisories
- Release notes in CHANGELOG.md

## Contact

For security-related questions or concerns:

- Security Team: security@bitrun.ai (if available)
- GitHub Issues: For non-sensitive security questions only
