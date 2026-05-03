{{/*
Common labels
*/}}
{{- define "console-frontend.labels" -}}
app.kubernetes.io/name: console-frontend
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "console-frontend.selectorLabels" -}}
app.kubernetes.io/name: console-frontend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "console-frontend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "console-frontend" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
