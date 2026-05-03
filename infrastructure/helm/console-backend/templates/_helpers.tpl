{{/*
Common labels
*/}}
{{- define "console-backend.labels" -}}
app.kubernetes.io/name: console-backend
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "console-backend.selectorLabels" -}}
app.kubernetes.io/name: console-backend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "console-backend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "console-backend" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
