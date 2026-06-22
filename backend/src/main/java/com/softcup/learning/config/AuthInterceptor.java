package com.softcup.learning.config;

import com.alibaba.fastjson2.JSONObject;
import com.softcup.learning.util.JwtUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    private static final String[] PUBLIC_PATHS = {
            "/api/auth/login",
            "/api/auth/register",
            "/api/health",
            "/api/path/sync-from-profile"
    };

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        String path = request.getRequestURI();
        if (path.startsWith("/api/public/demo/")) {
            return true;
        }
        for (String p : PUBLIC_PATHS) {
            if (path.equals(p)) {
                return true;
            }
        }
        String auth = request.getHeader("Authorization");
        if (auth == null || auth.isBlank()) {
            response.setStatus(401);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":401,\"message\":\"请先登录\"}");
            return false;
        }
        try {
            JSONObject payload = JwtUtil.parseToken(auth);
            request.setAttribute("userId", payload.getLong("sub"));
            request.setAttribute("userRole", payload.getString("role"));
            request.setAttribute("username", payload.getString("username"));
            return true;
        } catch (IllegalArgumentException e) {
            response.setStatus(401);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":401,\"message\":\"" + e.getMessage() + "\"}");
            return false;
        }
    }
}
