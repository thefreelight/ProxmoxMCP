#!/bin/bash
# n8n Workflow Automation Platform Deployment Script
# Deploy n8n on Kubernetes cluster

set -e

echo "🔧 Deploying n8n Workflow Automation Platform..."

# Create n8n namespace
kubectl create namespace n8n --dry-run=client -o yaml | kubectl apply -f -

# Create n8n ConfigMap
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: n8n-config
  namespace: n8n
data:
  N8N_HOST: "n8n.company.local"
  N8N_PORT: "5678"
  N8N_PROTOCOL: "https"
  WEBHOOK_URL: "https://n8n.company.local"
  GENERIC_TIMEZONE: "Asia/Shanghai"
  N8N_METRICS: "true"
  N8N_LOG_LEVEL: "info"
  N8N_USER_MANAGEMENT_DISABLED: "false"
  N8N_PUBLIC_API_DISABLED: "false"
  N8N_DISABLE_PRODUCTION_MAIN_PROCESS: "false"
  EXECUTIONS_PROCESS: "main"
  EXECUTIONS_MODE: "regular"
  N8N_ENCRYPTION_KEY: "n8n-encryption-key-change-this"
EOF

# Create n8n Secret for database connection
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: n8n-secrets
  namespace: n8n
type: Opaque
stringData:
  DB_TYPE: "postgresdb"
  DB_POSTGRESDB_HOST: "192.168.0.106"
  DB_POSTGRESDB_PORT: "5432"
  DB_POSTGRESDB_DATABASE: "n8n"
  DB_POSTGRESDB_USER: "n8n"
  DB_POSTGRESDB_PASSWORD: "N8nDB123!"
  N8N_BASIC_AUTH_ACTIVE: "true"
  N8N_BASIC_AUTH_USER: "admin"
  N8N_BASIC_AUTH_PASSWORD: "n8nAdmin123!"
EOF

# Create n8n PersistentVolumeClaim
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: n8n-data
  namespace: n8n
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF

# Create n8n Deployment
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: n8n
  namespace: n8n
  labels:
    app: n8n
spec:
  replicas: 1
  selector:
    matchLabels:
      app: n8n
  template:
    metadata:
      labels:
        app: n8n
    spec:
      containers:
      - name: n8n
        image: n8nio/n8n:latest
        ports:
        - containerPort: 5678
        envFrom:
        - configMapRef:
            name: n8n-config
        - secretRef:
            name: n8n-secrets
        volumeMounts:
        - name: n8n-data
          mountPath: /home/node/.n8n
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 5678
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 5678
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: n8n-data
        persistentVolumeClaim:
          claimName: n8n-data
EOF

# Create n8n Service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: n8n-service
  namespace: n8n
  labels:
    app: n8n
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5678
    protocol: TCP
    name: http
  selector:
    app: n8n
EOF

# Create n8n Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-ingress
  namespace: n8n
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - n8n.company.local
    secretName: n8n-tls
  rules:
  - host: n8n.company.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: n8n-service
            port:
              number: 80
EOF

# Wait for deployment to be ready
echo "⏳ Waiting for n8n deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/n8n -n n8n

# Get service information
echo "✅ n8n deployment completed!"
echo ""
echo "📋 n8n Service Information:"
kubectl get svc -n n8n
echo ""
echo "🌐 Access URLs:"
echo "  Internal: http://n8n-service.n8n.svc.cluster.local"
echo "  External: https://n8n.company.local"
echo ""
echo "🔑 Default Credentials:"
echo "  Username: admin"
echo "  Password: n8nAdmin123!"
echo ""
echo "📊 Pod Status:"
kubectl get pods -n n8n
