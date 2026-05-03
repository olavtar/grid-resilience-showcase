{{/*
Common labels
*/}}
{{- define "risk-engine.labels" -}}
app.kubernetes.io/name: risk-engine
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "risk-engine.selectorLabels" -}}
app.kubernetes.io/name: risk-engine
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "risk-engine.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "risk-engine" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
