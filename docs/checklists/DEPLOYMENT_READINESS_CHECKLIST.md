# Deployment Readiness Checklist

This checklist is used before promoting Microsoft Fabric changes through the Azure DevOps CI/CD pipeline.

Most deployment issues are caused by missing prerequisites, incorrect configuration, or environment inconsistencies rather than problems in the deployment code itself.

Use this checklist before running the pipeline.

---

# 1. Microsoft Fabric Environment

Verify the following:

- [ ] Microsoft Fabric Capacity is available and assigned.
- [ ] Development (DEV), User Acceptance Testing (UAT), and Production (PROD) workspaces have been created.
- [ ] Only the **Development (DEV)** workspace is connected to Git.
- [ ] UAT and PROD are deployment targets only and are **not** connected to Git.
- [ ] Workspace GUIDs have been verified for all environments.
- [ ] Deployment scope matches the intended target workspace.

---

# 2. Identity & Security

Verify the following:

- [ ] Microsoft Entra ID Application has been created.
- [ ] Service Principal (SPN) has been created.
- [ ] Service Principal credentials are stored securely.
- [ ] Required Microsoft Entra ID API permissions have been granted.
- [ ] Directory Readers permission has been assigned (where required by the implementation).
- [ ] Admin consent has been granted for required API permissions.
- [ ] Service Principal has been added to the DEV workspace.
- [ ] Service Principal has been added to the UAT workspace.
- [ ] Service Principal has been added to the PROD workspace.
- [ ] Service Principal has the required Fabric workspace permissions.

---

# 3. Azure DevOps Configuration

Verify the following:

- [ ] Azure DevOps Repository has been configured.
- [ ] Git branching strategy has been configured.
- [ ] Branch Policies have been configured.
- [ ] Microsoft Fabric connection to Azure DevOps has been created.
- [ ] Azure DevOps Service Connection has been created.
- [ ] Pipeline permissions have been configured.
- [ ] Environment-specific Variable Groups have been created.
- [ ] Variable Groups contain the correct Workspace GUIDs.
- [ ] Secrets are stored as secret variables.
- [ ] Approval Gates have been configured (where required).

---

# 4. Deployment Configuration

Verify the following:

- [ ] Required Python version is installed.
- [ ] Required Python libraries have been installed.
- [ ] Azure DevOps Agent satisfies the runtime requirements.
- [ ] `deploy_workspace_fabric.py` is configured correctly.
- [ ] Deployment scope has been reviewed.
- [ ] Validation mode has been tested before deployment.
- [ ] Environment configuration has been reviewed before promotion.

---

# 5. Deployment Validation

Before promoting to higher environments, verify:

- [ ] Pull Request validation completed successfully.
- [ ] Validation pipeline completed successfully.
- [ ] No validation errors remain.
- [ ] Deployment logs have been reviewed.

---

# 6. Post-Deployment Verification

After deployment completes, verify:

- [ ] Expected Fabric items have been deployed.
- [ ] Environment-specific configuration has been applied correctly.
- [ ] Deployment completed without errors.
- [ ] Workspace content matches the source repository.
- [ ] No unexpected items were removed.
- [ ] Manual verification of the target workspace has been completed.

---

# Common Deployment Issues

Before troubleshooting the deployment code, verify these common causes:

- Incorrect Workspace GUID.
- Service Principal missing Fabric workspace permissions.
- Missing Microsoft Entra ID API permissions.
- Directory Readers permission not assigned (where required).
- Incorrect Variable Group values.
- Branch strategy does not match the deployment flow.
- Multiple Fabric workspaces connected directly to Git.
- Incorrect deployment scope.
- Required secrets not available during pipeline execution.

---

# Scope

This checklist covers promoting Microsoft Fabric items through Azure DevOps with
a service principal: workspaces, identity, variable groups, branch strategy, and
the deployment scope itself.

It does not cover warehouse schema deployment, which is deliberately excluded
from the publish scope because a `fabric-cicd` publish can reset schema.

---

> **Tip:** Completing this checklist before deployment is significantly faster than troubleshooting a failed deployment afterward.
