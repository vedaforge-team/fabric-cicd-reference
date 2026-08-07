# Release Checklist

- [x] Fabric capacity / workspaces ready
- [x] DEV workspace connected to Git
- [x] UAT / PROD not independently Git-connected
- [x] Service Principal created
- [x] Required Microsoft Entra permissions / roles configured
- [x] SPN granted the appropriate Fabric workspace access
- [x] DEV / UAT / PROD workspace GUIDs verified
- [x] Environment Variable Groups created
- [x] Pipeline has permission to the required variable groups
- [x] Secret values protected
- [x] Branch strategy configured
- [x] Service connection / pipeline permissions ready
- [x] Azure DevOps agent available and meets requirements
- [x] Required Python / library dependencies available
- [x] Approval gate configured where required
- [x] Deployment scope matches `deploy_workspace_fabric.py`
- [x] Warehouse is intentionally excluded from the publish scope
