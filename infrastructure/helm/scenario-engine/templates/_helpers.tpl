{{/*
Common labels
*/}}
{{- define "scenario-engine.labels" -}}
app.kubernetes.io/name: scenario-engine
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "scenario-engine.selectorLabels" -}}
app.kubernetes.io/name: scenario-engine
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "scenario-engine.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "scenario-engine" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
