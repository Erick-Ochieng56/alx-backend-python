#!/bin/bash

echo "=== Django CrashLoopBackOff Diagnosis & Fix ==="

# Check pod logs to understand why they're crashing
echo "1. Checking pod logs for crash reasons..."
echo ""

# Get logs from the most recent pod
LATEST_POD=$(kubectl get pods -l app=django-messaging-app --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
echo "--- Logs from latest pod: $LATEST_POD ---"
kubectl logs $LATEST_POD --tail=50
echo ""

# Check previous container logs (from before the last crash)
echo "--- Previous container logs (before crash) ---"
kubectl logs $LATEST_POD --previous --tail=50 2>/dev/null || echo "No previous logs available"
echo ""

# Show pod description to see restart reason
echo "2. Pod description (showing restart reasons):"
kubectl describe pod $LATEST_POD | grep -A 10 -B 10 "Last State\|State\|Restart"
echo ""

# Check for resource issues
echo "3. Checking resource constraints..."
kubectl describe pod $LATEST_POD | grep -A 5 -B 5 "Limits\|Requests\|QoS"
echo ""

# List all deployments (you seem to have multiple)
echo "4. Current deployments:"
kubectl get deployments
echo ""

# Check services
echo "5. Current services:"
kubectl get services
echo ""

echo "=== RECOMMENDED FIXES ==="
echo ""

echo "STEP 1: Clean up duplicate deployments"
echo "You have multiple deployments. Let's clean them up:"
echo ""
echo "# Delete the blue deployment (seems to be a duplicate)"
echo "kubectl delete deployment django-messaging-app-blue"
echo ""
echo "# Scale main deployment to 0 to stop crashes temporarily"
echo "kubectl scale deployment django-messaging-app --replicas=0"
echo ""

echo "STEP 2: Common Django crash fixes"
echo ""

echo "A) Database connection issues:"
echo "   - Ensure database is accessible"
echo "   - Check DATABASE_URL environment variable"
echo "   - Verify database migrations are applied"
echo ""

echo "B) Missing environment variables:"
echo "   kubectl get deployment django-messaging-app -o yaml | grep -A 20 env"
echo ""

echo "C) Port binding issues:"
echo "   - Ensure Django is binding to 0.0.0.0:8000 (not 127.0.0.1)"
echo "   - Check if ALLOWED_HOSTS includes the service IP"
echo ""

echo "D) Missing static files or media:"
echo "   - Ensure collectstatic was run during image build"
echo "   - Check for missing dependencies in requirements.txt"
echo ""

echo "STEP 3: Quick diagnostic commands to run:"
echo ""
echo "# Check deployment configuration"
echo "kubectl get deployment django-messaging-app -o yaml"
echo ""
echo "# Check configmaps and secrets"
echo "kubectl get configmaps"
echo "kubectl get secrets"
echo ""
echo "# Test with a simple command to see if container starts"
echo "kubectl run django-debug --image=\$(kubectl get deployment django-messaging-app -o jsonpath='{.spec.template.spec.containers[0].image}') --rm -it --restart=Never -- /bin/bash"
echo ""

echo "STEP 4: Fix and restart"
echo "After identifying the issue:"
echo ""
echo "# Apply fixes to deployment.yaml and redeploy"
echo "kubectl apply -f deployment.yaml"
echo ""
echo "# Or restart with current config"
echo "kubectl scale deployment django-messaging-app --replicas=1"
echo "kubectl rollout status deployment/django-messaging-app --timeout=300s"
echo ""

echo "=== IMMEDIATE ACTION COMMANDS ==="
echo ""
echo "Run these commands now:"
echo ""
echo "1. kubectl delete deployment django-messaging-app-blue"
echo "2. kubectl scale deployment django-messaging-app --replicas=0"
echo "3. # Fix the underlying issue based on logs above"
echo "4. kubectl scale deployment django-messaging-app --replicas=1"
echo ""

# Automatically clean up the blue deployment if user wants
read -p "Do you want to automatically delete the duplicate 'django-messaging-app-blue' deployment? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deleting django-messaging-app-blue deployment..."
    kubectl delete deployment django-messaging-app-blue
    echo "Done!"
fi

echo ""
echo "=== Next Steps ==="
echo "1. Review the logs above to identify the specific crash reason"
echo "2. Fix the underlying issue (database, environment variables, etc.)"
echo "3. Test with a single replica first"
echo "4. Scale up gradually once stable"