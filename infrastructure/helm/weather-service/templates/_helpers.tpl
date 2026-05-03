{{/*
Common labels
*/}}
{{- define "weather-service.labels" -}}
app.kubernetes.io/name: weather-service
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: grid-resilience
{{- end }}

{{/*
Selector labels
*/}}
{{- define "weather-service.selectorLabels" -}}
app.kubernetes.io/name: weather-service
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "weather-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default "weather-service" .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
