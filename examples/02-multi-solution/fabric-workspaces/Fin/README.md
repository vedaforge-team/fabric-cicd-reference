# FIN solution artifacts

This folder is populated by Microsoft Fabric, not by hand.

Connect the **Fin-Development** workspace to this repository using Fabric Git
integration, with the Git folder set to `/fabric-workspaces/Fin`, then commit its items from
Fabric. They will appear here as `<Item Name>.<ItemType>/` folders, each
containing a `.platform` descriptor.

Until that happens this folder holds no Fabric items, and the empty-source guard
in `scripts/deploy_fabric_workspace.py` will refuse to deploy it. That is
intentional: deploying an empty folder with orphan removal enabled would empty
the target workspace.

This README does not trigger a deployment. Markdown is in the change-detection
ignore list, so documentation changes never reach a workspace.
